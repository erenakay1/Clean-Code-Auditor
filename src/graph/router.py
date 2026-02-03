"""
router.py
---------
Critic sonrasi routing logic — PURE FUNCTION.
State mutation yok burada. Sadece karar veriyor.
retry_count increment → retry_node'da yapilir.
"""

from src.graph.state import PipelineState
from src.core.constants import MAX_CRITIC_RETRIES


def critic_router(state: PipelineState) -> str:
    """
    Conditional edge: critic -> ?

    Returns:
        "retry"  -> retry_node'a git (counter artir, sonra analyst)
        "fixer"  -> onaylandı veya max retry asildi
    """

    # Case 1: Critic onayladı
    if state["approved"]:
        return "fixer"

    # Case 2: Onaylanmadi ama retry kalan var
    if state["retry_count"] < MAX_CRITIC_RETRIES:
        return "retry"

    # Case 3: Max retry asildi
    return "fixer"