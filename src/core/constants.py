# src/core/constants.py - TAM DOSYA (eski yerine bu gelecek)

"""
constants.py
────────────
Tüm sabit değerler burada. Magic number yok.
"""

# ─── QUICK TEST MODE (YENI!) ────────────────────────────
QUICK_TEST_MODE: bool = True  # False yapınca normal mod

# ─── GitHub Fetcher ──────────────────────────────────────
TARGET_EXTENSIONS: set[str] = {".cs", ".csproj"}

# Quick mode'da dosya limitleri DAHA DÜŞÜK
if QUICK_TEST_MODE:
    MAX_FILE_SIZE_BYTES: int = 30_000      # 30KB (hızlı test)
    MAX_FILES_LIMIT: int = 8               # Max 8 dosya
    MAX_CONTEXT_CHARS: int = 40_000        # 40k char (10k token)
    MAX_FILE_CHARS: int = 8_000            # Dosya başına 8k
else:
    MAX_FILE_SIZE_BYTES: int = 500_000     # Normal: 500KB
    MAX_FILES_LIMIT: int = 50              # Normal: 50 dosya
    MAX_CONTEXT_CHARS: int = 60_000
    MAX_FILE_CHARS: int = 10_000

MAX_TREE_DEPTH: int = 8

SKIP_DIRECTORIES: set[str] = {
    "node_modules", "bin", "obj", ".git",
    "packages", "vendor", "__pycache__",
}

# ─── Agent Pipeline ─────────────────────────────────────
# KRITIK: Quick mode'da retry YOK!
MAX_CRITIC_RETRIES: int = 2 if QUICK_TEST_MODE else 3

# ─── LLM ─────────────────────────────────────────────────
DEFAULT_MODEL: str = "gpt-4o-mini"
DEFAULT_TEMPERATURE: float = 0.0  # Sıfır = en hızlı

# ─── Prompt File Paths ───────────────────────────────────
import os

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")

PROMPT_ANALYST_PATH = os.path.normpath(os.path.join(_PROMPTS_DIR, "analyst.txt"))
PROMPT_CRITIC_PATH  = os.path.normpath(os.path.join(_PROMPTS_DIR, "critic.txt"))
PROMPT_FIXER_PATH   = os.path.normpath(os.path.join(_PROMPTS_DIR, "fixer.txt"))