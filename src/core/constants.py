"""
constants.py
────────────
Tüm sabit değerler burada. Magic number yok.
"""

# ─── GitHub Fetcher ──────────────────────────────────────
TARGET_EXTENSIONS: set[str] = {".cs", ".csproj"}
MAX_FILE_SIZE_BYTES: int    = 500_000          # 500 KB
MAX_TREE_DEPTH: int         = 8                # recursive dir gezme limiti

SKIP_DIRECTORIES: set[str] = {
    "node_modules", "bin", "obj", ".git",
    "packages", "vendor", "__pycache__",
}

# ─── Token Budget ────────────────────────────────────────
# gpt-4o-mini → 1M TPM, 128k context window → çok rahat
# Ama yine de context'i sane tutalalım: ~15k token input hedef
# 1 token ≈ 4 char  →  15_000 * 4 = 60_000 char max
MAX_CONTEXT_CHARS: int  = 60_000               # tüm dosyalar toplam char limiti
MAX_FILE_CHARS: int     = 10_000               # tek dosya max char

# ─── Agent Pipeline ─────────────────────────────────────
MAX_CRITIC_RETRIES: int = 2                    # Critic retry loop limiti

# ─── LLM ─────────────────────────────────────────────────
# gpt-4o-mini: TPM limit çok yüksek, cost düşük, .NET analiz kalitesi yeterli
DEFAULT_MODEL: str      = "gpt-4o-mini"
DEFAULT_TEMPERATURE: float = 0.2               # düşük → tutarlı analiz

# ─── Prompt File Paths ───────────────────────────────────
import os

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")

PROMPT_ANALYST_PATH = os.path.normpath(os.path.join(_PROMPTS_DIR, "analyst.txt"))
PROMPT_CRITIC_PATH  = os.path.normpath(os.path.join(_PROMPTS_DIR, "critic.txt"))
PROMPT_FIXER_PATH   = os.path.normpath(os.path.join(_PROMPTS_DIR, "fixer.txt"))