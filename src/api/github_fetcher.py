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

from enum import Enum
from typing import Literal

class FetchMode(str, Enum):
    REPO = "repo"
    FILE = "file"

logger = logging.getLogger(__name__)

# ─── Retry config ────────────────────────────────────────
MAX_RETRIES      = 3
BACKOFF_SECONDS  = [2, 5, 10]        # her retry'de artan bekle


def detect_fetch_mode(url: str) -> tuple[FetchMode, str]:
    """
    URL'den fetch modunu otomatik tespit eder.
    
    Returns:
        (mode, clean_url)
        
    Kurallar:
    - URL .cs ile bitiyorsa → FILE mode
    - URL /tree/ veya /blob/ içeriyorsa ve .cs bitiyorsa → FILE mode
    - Diğer durumlar → REPO mode
    """
    url = url.strip()
    
    # .cs dosyası mı?
    if url.endswith(".cs") or url.endswith(".csproj"):
        return FetchMode.FILE, url
    
    # /blob/ veya /tree/ içinde dosya path'i var mı?
    if "/blob/" in url or "/tree/" in url:
        # Son segment'e bak
        last_part = url.split("/")[-1]
        if "." in last_part:  # Uzantılı dosya
            return FetchMode.FILE, url
    
    return FetchMode.REPO, url

# ─── Client ──────────────────────────────────────────────
def _get_client() -> Github:
    """Token varsa authenticated, yoksa anonymous."""
    token = settings.GITHUB_TOKEN
    return Github(token) if token else Github()


# ─── URL Parser ──────────────────────────────────────────
def parse_repo_url(url: str) -> tuple[str, str]:
    """
    GitHub URL'sinden owner ve repo çıkarır.
    Artık dosya path'lerini de handle eder.
    """
    url = url.strip()
    
    if "github.com/" not in url:
        raise ValueError("URL 'github.com' içermelidir.")
    
    after_domain = url.split("github.com/", 1)[1]
    
    # .git varsa temizle
    if ".git" in after_domain:
        after_domain = after_domain.split(".git")[0]
    
    parts = after_domain.split("/")
    
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(
            "Geçersiz GitHub URL.\n"
            "Beklenen: https://github.com/user/repo"
        )
    
    owner = parts[0]
    repo = parts[1]
    
    return owner, repo

def parse_file_path(url: str) -> str:
    """
    GitHub URL'sinden dosya path'ini çıkarır.
    
    Örnek:
    https://github.com/user/repo/blob/main/src/Program.cs
    → "src/Program.cs"
    
    https://github.com/user/repo.git/master/UniversityTinder/Program.cs
    → "UniversityTinder/Program.cs"
    """
    url = url.strip()
    
    # .git/ sonrasını al
    if ".git/" in url:
        after_git = url.split(".git/", 1)[1]
        # master/ veya main/ gibi branch ismini atla
        parts = after_git.split("/")
        if len(parts) > 1:
            return "/".join(parts[1:])  # branch adını at
        return after_git
    
    # /blob/ veya /tree/ sonrasını al
    if "/blob/" in url:
        return url.split("/blob/", 1)[1].split("/", 1)[1]  # branch'ı atla
    
    if "/tree/" in url:
        return url.split("/tree/", 1)[1].split("/", 1)[1]
    
    raise ValueError(
        f"Dosya path'i çıkarılamadı: {url}\n"
        "Beklenen format: .../blob/main/path/file.cs"
    )


def fetch_single_file(repo_url: str) -> dict[str, str]:
    """
    Sadece belirtilen dosyayı çeker.
    
    Returns:
        {file_path: content}
    """
    owner, repo_name = parse_repo_url(repo_url)
    file_path = parse_file_path(repo_url)
    
    client = _get_client()
    repo = _with_retry(client.get_repo, f"{owner}/{repo_name}")
    
    try:
        file_content = _with_retry(repo.get_contents, file_path)
        content = file_content.decoded_content.decode("utf-8")
        
        logger.info(f"✅ Dosya çekildi: {file_path}")
        return {file_path: content}
        
    except GithubException as e:
        if e.status == 404:
            raise ValueError(
                f"Dosya bulunamadı: {file_path}\n"
                f"Repo: {owner}/{repo_name}\n"
                "Path'i kontrol edin."
            )
        raise


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
    Otomatik mod tespiti ile fetch yapar:
    - .cs dosyası → sadece o dosya
    - repo URL → tüm .cs dosyaları
    """
    mode, clean_url = detect_fetch_mode(repo_url)
    
    if mode == FetchMode.FILE:
        logger.info("📄 Single File Mode")
        return fetch_single_file(clean_url)
    else:
        logger.info("📦 Repo Mode")
        return _fetch_repo_files(clean_url)

def _fetch_repo_files(repo_url: str) -> dict[str, str]:
    """
    Repo'daki tüm .cs / .csproj dosyalarını çeker.
    (Eski fetch_target_files mantığı)
    """
    from src.core.constants import MAX_FILES_LIMIT
    
    owner, repo_name = parse_repo_url(repo_url)
    client = _get_client()
    repo = _with_retry(client.get_repo, f"{owner}/{repo_name}")

    files: dict[str, str] = {}
    _walk_tree(repo, path="", files=files, depth=0, max_files=MAX_FILES_LIMIT)

    if not files:
        raise ValueError(
            f"Repo'da {TARGET_EXTENSIONS} uzantili dosya bulunamadı."
        )

    logger.info(f"✅ Toplam {len(files)} dosya çekildi.")
    return files


# ─── Recursive Tree Walker ───────────────────────────────
def _walk_tree(
    repo,
    path: str,
    files: dict[str, str],
    depth: int,
    max_files: int = 999,  # Yeni parametre!
) -> None:
    """Repo tree'yi gezir, max_files limitine ulaşınca durur."""

    if depth > MAX_TREE_DEPTH:
        return
    
    # Limit kontrolü - YENI!
    if len(files) >= max_files:
        logger.info(f"⚠️ Dosya limiti ({max_files}) doldu, durduruldu.")
        return

    try:
        contents = _with_retry(repo.get_contents, path)
    except RuntimeError as e:
        logger.warning(f"  [SKIP] {path}: {e}")
        files[path] = f"// [NETWORK ERROR] Bu path cekilemedi: {path}"
        return
    except GithubException:
        return

    if not isinstance(contents, list):
        contents = [contents]

    for item in contents:
        # Her item'de tekrar kontrol - YENI!
        if len(files) >= max_files:
            break
            
        if item.type == "dir":
            if item.name.lower() in SKIP_DIRECTORIES:
                continue
            _walk_tree(repo, item.path, files, depth + 1, max_files)  # max_files'ı geç

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