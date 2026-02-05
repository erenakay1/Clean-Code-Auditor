"""
llm.py
──────
LLM client factory. Tüm agent node'ları buradan LLM alır.
Model veya temperature değiştirmek → sadece burada.
"""

from langchain_openai import ChatOpenAI

from src.core.config import settings
from src.core.constants import DEFAULT_MODEL, DEFAULT_TEMPERATURE


def get_llm(streaming: bool = False) -> ChatOpenAI:
    return ChatOpenAI(
        model=DEFAULT_MODEL,
        temperature=DEFAULT_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY,
        streaming=streaming,  # Streamlit'te göster
        request_timeout=30,   # 30s timeout
    )