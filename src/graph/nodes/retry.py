"""
retry.py - Retry Node
----------------------
retry_count'u artiran tek node.
trace_log'a yazar, sonra Analyst'e gecer (graph.py'de edge tanimlanir).
"""

from src.graph.state import PipelineState
from src.core.constants import MAX_CRITIC_RETRIES


def retry_node(state: PipelineState) -> dict:
    """
    retry_count += 1  yap ve trace log'a yaz.
    """
    new_count = state["retry_count"] + 1

    return {
        "retry_count": new_count,
        "trace_log": [{
            "agent":   "Retry",
            "step":    "retry_loop",
            "message": (
                f"Critic onaylamadi. "
                f"Retry {new_count}/{MAX_CRITIC_RETRIES} — Analyst'e tekrar gönderildi."
            ),
        }],
    }