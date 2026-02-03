"""
state.py
--------
LangGraph pipeline'in state'i.

LangGraph 1.x state management:
  - Node bir dict return eder, sadece degistigi keys ile
  - list fields → Annotated[list, operator.add] ile append reducer
  - scalar fields → sadece yeni value return et, overwrite olur
"""

from typing import Annotated
from typing_extensions import TypedDict
import operator


class PipelineState(TypedDict):
    """Multi-agent pipeline state."""

    # ── Input ───────────────────────────────────────────
    files_context: str              # GitHub'dan cekilen dosyalarin formatlanmis stringi

    # ── Agent Outputs (raw JSON strings) ────────────────
    analyst_output: str             # Agent A ciktisi
    critic_output:  str             # Agent B ciktisi
    fixer_output:   str             # Agent C ciktisi

    # ── Flow Control ────────────────────────────────────
    retry_count: int                # Critic -> Analyst loop sayisi
    approved:    bool               # Critic onay flag'i

    # ── Logging ─────────────────────────────────────────
    # Annotated + operator.add → her node'un return'undeki list
    # onceki list'e APPEND edilir (overwrite degil)
    trace_log: Annotated[list[dict], operator.add]