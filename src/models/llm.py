"""
llm.py
──────
LLM client factory. Tüm agent node'ları buradan LLM alır.
Model veya temperature değiştirmek → sadece burada.
"""

from langchain_openai import ChatOpenAI

from src.core.config import settings
from src.core.constants import DEFAULT_MODEL, DEFAULT_TEMPERATURE


def get_llm(
    model: str | None = None,
    temperature: float | None = None,
) -> ChatOpenAI:
    """
    ChatOpenAI instance döner.

    Args:
        model:       override edilmek istenirse (default: gpt-4o)
        temperature: override edilmek istenirse (default: 0.2)
    """
    return ChatOpenAI(
        model=model or DEFAULT_MODEL,
        temperature=temperature if temperature is not None else DEFAULT_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY,
    )