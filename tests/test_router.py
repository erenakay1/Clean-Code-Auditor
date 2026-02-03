"""
test_router.py
--------------
router (pure decision) + retry_node (state mutation) + full loop test.
LangGraph 1.x state merge pattern simule edilir.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.graph.router import critic_router
from src.graph.nodes.retry import retry_node
from src.core.constants import MAX_CRITIC_RETRIES


def _make_state(approved: bool, retry_count: int) -> dict:
    return {
        "files_context":  "...",
        "analyst_output": "{}",
        "critic_output":  "{}",
        "fixer_output":   "",
        "retry_count":    retry_count,
        "approved":       approved,
        "trace_log":      [],
    }


def _merge(state: dict, node_return: dict) -> dict:
    """LangGraph 1.x merge logic simulation."""
    for key, val in node_return.items():
        if key == "trace_log":
            state[key] = state[key] + val   # reducer: append
        else:
            state[key] = val
    return state


# ─── Router: pure decision ───────────────────────────────
class TestCriticRouter:

    def test_approved_goes_to_fixer(self):
        assert critic_router(_make_state(True, 0)) == "fixer"

    def test_not_approved_goes_to_retry(self):
        assert critic_router(_make_state(False, 0)) == "retry"

    def test_not_approved_retry1_goes_to_retry(self):
        assert critic_router(_make_state(False, 1)) == "retry"

    def test_max_retry_goes_to_fixer(self):
        assert critic_router(_make_state(False, MAX_CRITIC_RETRIES)) == "fixer"

    def test_approved_after_retries_goes_to_fixer(self):
        assert critic_router(_make_state(True, 2)) == "fixer"

    def test_router_does_not_mutate_state(self):
        state = _make_state(False, 0)
        critic_router(state)
        assert state["retry_count"] == 0
        assert state["trace_log"]   == []


# ─── Retry Node: returns correct dict ────────────────────
class TestRetryNode:

    def test_returns_incremented_count(self):
        state  = _make_state(False, 0)
        result = retry_node(state)
        assert result["retry_count"] == 1

    def test_does_not_mutate_input(self):
        state  = _make_state(False, 0)
        retry_node(state)
        assert state["retry_count"] == 0     # input untouched

    def test_returns_trace_log_list(self):
        result = retry_node(_make_state(False, 0))
        assert len(result["trace_log"]) == 1
        assert result["trace_log"][0]["agent"] == "Retry"

    def test_count_from_1_to_2(self):
        result = retry_node(_make_state(False, 1))
        assert result["retry_count"] == 2


# ─── Full loop with LangGraph merge simulation ──────────
class TestFullRetryLoop:

    def test_loop_exits_after_max_retries(self):
        state = _make_state(False, 0)

        for _ in range(10):
            decision = critic_router(state)
            if decision == "fixer":
                break
            state = _merge(state, retry_node(state))

        assert decision          == "fixer"
        assert state["retry_count"] == MAX_CRITIC_RETRIES
        assert len(state["trace_log"]) == MAX_CRITIC_RETRIES

    def test_loop_exits_immediately_on_approve(self):
        state    = _make_state(True, 0)
        decision = critic_router(state)
        assert decision          == "fixer"
        assert state["retry_count"] == 0
        assert state["trace_log"]   == []