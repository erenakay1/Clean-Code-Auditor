"""
config.py
─────────
App-wide configuration. Env var'lar burada yüklenir.
Tek bir yerden erişilir → import config; config.settings.OPENAI_API_KEY
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable settings. App startup'ta bir kez oluşur."""

    # ── Keys ──────────────────────────────────────────
    OPENAI_API_KEY:    str = os.getenv("OPENAI_API_KEY", "")
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    GITHUB_TOKEN:      str = os.getenv("GITHUB_TOKEN", "")

    # ── LangSmith ─────────────────────────────────────
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "clean-code-auditor")

    # ── Validation ────────────────────────────────────
    @property
    def openai_ok(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def langsmith_ok(self) -> bool:
        return bool(self.LANGSMITH_API_KEY)

    @property
    def github_token_ok(self) -> bool:
        return bool(self.GITHUB_TOKEN)


# ─── Singleton ───────────────────────────────────────────
settings = Settings()