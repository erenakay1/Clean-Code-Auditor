"""
analyst.py - Agent A: Analyst
-----------------------------
Kodu okur, SOLID + Clean Architecture + .NET best practices analiz eder.

Retry logic:
  - retry_count == 0 → fresh analiz
  - retry_count > 0  → Critic'in missed_issues feedback'ini dahil et
                       Analyst artık ne eksik kaldığını bilir
"""

from src.graph.state import PipelineState
from src.models.llm import get_llm
from src.services.prompt_loader import load_prompt


# ── İlk analiz (retry yok) ──────────────────────────────
_TEMPLATE_FRESH = """Analiz edilecek dosyalar:

{files_context}

Lutfen yukaridaki kriterlere gore tam analiz yap ve JSON formatinda dondur."""


# ── Retry analiz (Critic feedback dahil) ─────────────────
_TEMPLATE_RETRY = """Analiz edilecek dosyalar:

{files_context}

─────────────────────────

Onceki analizin eksik kaldı. Critic'in tespit ettigi missed issues:

{critic_feedback}

Lutfen yukaridaki eksiklikleri de dahil ederek TAM ve KAPSAMLI bir analiz yap.
Onceki analizinde zaten bulan sorunları da tekrar dahil et.
JSON formatinda dondur."""


def analyst_node(state: PipelineState) -> dict:
    """
    Agent A: Analyst node.
    - retry_count == 0 → fresh analiz
    - retry_count > 0  → Critic feedback ile retry analiz
    """
    llm           = get_llm()
    system_prompt = load_prompt("analyst")

    if state["retry_count"] == 0:
        # ── Fresh analiz ──────────────────────────────
        user_message = _TEMPLATE_FRESH.format(
            files_context=state["files_context"],
        )
    else:
        # ── Retry: Critic feedback dahil ──────────────
        user_message = _TEMPLATE_RETRY.format(
            files_context=state["files_context"],
            critic_feedback=state["critic_output"],   # Critic'in tam JSON output'u
        )

    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ])

    return {
        "analyst_output": response.content,
        "trace_log": [{
            "agent":           "Analyst",
            "step":            "analysis_complete",
            "retry_iteration": state["retry_count"],
            "is_retry":        state["retry_count"] > 0,
            "output_preview":  response.content[:400],
        }],
    }