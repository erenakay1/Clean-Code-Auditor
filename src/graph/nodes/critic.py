"""
critic.py - Agent B: Critic (Reflection)
-----------------------------------------
Analyst ciktisini denetler.
Eksik/yanlis varsa -> approved=False -> retry loop.
Her sey iyiyse -> approved=True -> Fixer'a gec.
"""

from src.graph.state import PipelineState
from src.models.llm import get_llm
from src.services.prompt_loader import load_prompt
from src.utils.parser import safe_json_parse


_USER_TEMPLATE = """Orijinal kaynak kodlar:

{files_context}

--------------------------

Agent A (Analyst) cikarigi analiz:

{analyst_output}

Lutfen bu analizi denet ve JSON formatinda dondur."""


def critic_node(state: PipelineState) -> dict:
    """
    Agent B: Critic node.
    Analyst ciktisini denet -> approved flag'ini set.
    """
    llm           = get_llm()
    system_prompt = load_prompt("critic")
    user_message  = _USER_TEMPLATE.format(
        files_context=state["files_context"],
        analyst_output=state["analyst_output"],
    )

    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ])

    raw_output = response.content

    # JSON parse -> approved flag cikar
    parsed   = safe_json_parse(raw_output)
    approved = parsed.get("critic_review", {}).get("approved", False)

    return {
        "critic_output": raw_output,
        "approved":      approved,
        "trace_log": [{
            "agent":          "Critic",
            "step":           "review_complete",
            "approved":       approved,
            "retry_count":    state["retry_count"],
            "output_preview": raw_output[:400],
        }],
    }