"""
prompt_loader.py
────────────────
prompts/ klasöründen .txt dosyaları okur ve cache'ler.
Agent node'ları burada load_prompt("analyst") der → string döner.
"""

import os
from functools import lru_cache

from src.core.constants import (
    PROMPT_ANALYST_PATH,
    PROMPT_CRITIC_PATH,
    PROMPT_FIXER_PATH,
)

# ─── Path mapping ────────────────────────────────────────
_PROMPT_PATHS: dict[str, str] = {
    "analyst": PROMPT_ANALYST_PATH,
    "critic":  PROMPT_CRITIC_PATH,
    "fixer":   PROMPT_FIXER_PATH,
}


@lru_cache(maxsize=8)
def load_prompt(name: str) -> str:
    """
    Prompt dosyasını oku ve döndür. İlk okumada cache'lenir.

    Args:
        name: "analyst" | "critic" | "fixer"

    Returns:
        Prompt text string

    Raises:
        KeyError:      Bilinmeyen prompt adı
        FileNotFoundError: Dosya yok
    """
    if name not in _PROMPT_PATHS:
        raise KeyError(
            f"Bilinmeyen prompt: '{name}'. "
            f"Geçerli: {list(_PROMPT_PATHS.keys())}"
        )

    path = _PROMPT_PATHS[name]

    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Prompt dosyası bulunamadı: {path}"
        )

    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()