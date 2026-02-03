"""
fixer.py - Agent C: Fixer
--------------------------
Onaylanan tum sorunlar icin iyilestirilmis .NET kodu yazar.
"""

import json

from src.graph.state import PipelineState
from src.models.llm import get_llm
from src.services.prompt_loader import load_prompt
from src.utils.parser import merge_issues


_USER_TEMPLATE = """Orijinal kaynak kodlar:

{files_context}

--------------------------

Onaylanan tum sorunlar (Analyst + Critic):

{approved_issues}

Lutfen her sorun icin iyilestirilmis kod yaz ve JSON formatinda dondur."""


def fixer_node(state: PipelineState) -> dict:
    """
    Agent C: Fixer node.
    Analyst + Critic sorunlarini birlestir -> LLM ile fix -> fixer_output'a yaz.
    """
    llm           = get_llm()
    system_prompt = load_prompt("fixer")

    # Analyst + Critic'in tum sorunlarini merge et
    all_issues   = merge_issues(state["analyst_output"], state["critic_output"])
    approved_str = json.dumps(all_issues, ensure_ascii=False, indent=2)

    user_message = _USER_TEMPLATE.format(
        files_context=state["files_context"],
        approved_issues=approved_str,
    )

    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ])

    return {
        "fixer_output": response.content,
        "trace_log": [{
            "agent":          "Fixer",
            "step":           "fixes_generated",
            "output_preview": response.content[:400],
        }],
    }