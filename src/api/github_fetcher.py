"""
github_fetcher.py
-----------------
GitHub repo'dan hedef dosyalari ceker.
Public repo -> token olmadan calisir.
Private repo -> GITHUB_TOKEN gerekir.

Retry & error handling:
  - Network errors (DNS, timeout, connection) -> retry with backoff
  - Rate limit 403 -> retry with backoff
  - Partial failures -> dosya skip, devam et
"""

import time
import logging
from github import Github, GithubException
from requests.exceptions import ConnectionError as ReqConnectionError

from src.core.config import settings
from src.core.constants import (
    TARGET_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    MAX_TREE_DEPTH,
    SKIP_DIRECTORIES,
    MAX_CONTEXT_CHARS,
    MAX_FILE_CHARS,
)

logger = logging.getLogger(__name__)

# ─── Retry config ────────────────────────────────────────
MAX_RETRIES      = 3
BACKOFF_SECONDS  = [2, 5, 10]        # her retry'de artan bekle


# ─── Client ──────────────────────────────────────────────
def _get_client() -> Github:
    """Token varsa authenticated, yoksa anonymous."""
    token = settings.GITHUB_TOKEN
    return Github(token) if token else Github()


# ─── URL Parser ──────────────────────────────────────────
def parse_repo_url(url: str) -> tuple[str, str]:
    """
    'https://github.com/user/repo' -> ('user', 'repo')
    """
    url = url.strip().rstrip("/").removesuffix(".git")
    parts = url.replace("https://github.com/", "").split("/")

    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            "Gecersiz GitHub URL.\n"
            "Beklenen format: https://github.com/user/repo"
        )

    return parts[0], parts[1]


# ─── Retry wrapper ──────────────────────────────────────
def _with_retry(func, *args, **kwargs):
    """
    Network hatalarında retry + exponential backoff.
    Catches: ConnectionError, GithubException (rate limit / transient)
    """
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except (ReqConnectionError, ConnectionError, OSError) as e:
            last_error = e
            logger.warning(
                f"Network hata (attempt {attempt+1}/{MAX_RETRIES}): {e}"
            )
        except GithubException as e:
            # 403 rate limit veya 500 server error -> retry
            if e.status in (403, 500, 502, 503):
                last_error = e
                logger.warning(
                    f"GitHub {e.status} (attempt {attempt+1}/{MAX_RETRIES}): {e.data}"
                )
            else:
                raise                          # 404 gibi -> direkt raise

        # backoff bekle
        if attempt < MAX_RETRIES - 1:
            wait = BACKOFF_SECONDS[attempt]
            logger.info(f"  -> {wait}s bekleyin, retry yapılıyor...")
            time.sleep(wait)

    raise RuntimeError(
        f"GitHub API'ye {MAX_RETRIES} kez deneme yapildı, hepsi başarısız.\n"
        f"Son hata: {last_error}\n"
        f"Internet bağlantınızı kontrol edip tekrar deneyin."
    )


# ─── Main Fetch ──────────────────────────────────────────
def fetch_target_files(repo_url: str) -> dict[str, str]:
    """
    Repo'daki tum .cs / .csproj dosyalarini ceker.
    Network hatalarında retry yapır.
    """
    owner, repo_name = parse_repo_url(repo_url)
    client = _get_client()

    # get_repo -> retry ile
    repo = _with_retry(client.get_repo, f"{owner}/{repo_name}")

    files: dict[str, str] = {}
    _walk_tree(repo, path="", files=files, depth=0)

    if not files:
        raise ValueError(
            f"Repo'da {TARGET_EXTENSIONS} uzantili dosya bulunamadı."
        )

    return files


# ─── Recursive Tree Walker ───────────────────────────────
def _walk_tree(
    repo,
    path: str,
    files: dict[str, str],
    depth: int,
) -> None:
    """Repo tree'yi recursive gezir, hedef dosyalari ceker."""

    if depth > MAX_TREE_DEPTH:
        return

    # get_contents -> retry ile
    try:
        contents = _with_retry(repo.get_contents, path)
    except RuntimeError as e:
        # max retry aşıldı ama tree walk devam edebilir
        logger.warning(f"  [SKIP] {path}: {e}")
        files[path] = f"// [NETWORK ERROR] Bu path cekilemedi: {path}"
        return
    except GithubException:
        return

    if not isinstance(contents, list):
        contents = [contents]

    for item in contents:
        if item.type == "dir":
            if item.name.lower() in SKIP_DIRECTORIES:
                continue
            _walk_tree(repo, item.path, files, depth + 1)

        elif item.type == "file":
            if not _is_target_file(item.name):
                continue

            if item.size > MAX_FILE_SIZE_BYTES:
                files[item.path] = (
                    f"// [SKIPPED] Dosya boyutu ({item.size} bytes) limiti astı."
                )
                continue

            try:
                files[item.path] = item.decoded_content.decode("utf-8")
            except Exception:
                files[item.path] = "// [ERROR] Dosya okunamadı."


def _is_target_file(filename: str) -> bool:
    """Dosya adı hedef uzantılardan birini mi taşıyor?"""
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in TARGET_EXTENSIONS)


# ─── Context Formatter (Token-Budget Aware) ─────────────
def format_files_context(files: dict[str, str]) -> str:
    """
    Dosyalari LLM prompt'a hazırlar.

    Smart truncation:
      1. Her dosya MAX_FILE_CHARS'a kesilir (basiı + sonu korunur)
      2. Toplam context MAX_CONTEXT_CHARS'ı aşamaz
      3. .csproj dosyalar öncelikli
      4. Kesilen dosyalara [TRUNCATED] notu düsürülür
    """
    sorted_files = sorted(
        files.items(),
        key=lambda item: (
            0 if item[0].lower().endswith(".csproj") else 1,
            len(item[1]),
        ),
    )

    chunks: list[str] = []
    total_chars       = 0

    for path, content in sorted_files:
        header = f"=== FILE: {path} ===\n"

        if len(content) > MAX_FILE_CHARS:
            keep_top    = MAX_FILE_CHARS // 2
            keep_bottom = MAX_FILE_CHARS // 2
            content = (
                content[:keep_top]
                + f"\n// ... [TRUNCATED: {len(content)} char -> {MAX_FILE_CHARS} char] ...\n"
                + content[-keep_bottom:]
            )

        block     = header + content
        block_len = len(block)

        if total_chars + block_len > MAX_CONTEXT_CHARS:
            remaining = MAX_CONTEXT_CHARS - total_chars
            if remaining > 200:
                block = block[:remaining] + "\n// [CONTEXT LIMIT - geri kalan dosyalar atlandı]"
                chunks.append(block)
            break

        chunks.append(block)
        total_chars += block_len

    return "\n\n".join(chunks)