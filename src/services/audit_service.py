"""
audit_service.py
────────────────
Ana orchestrator. Streamlit app'ı bu service'i çağırır.

Flow:
    repo_url → fetch files → format context → run pipeline → return state
"""

from src.api.github_fetcher import fetch_target_files, format_files_context
from src.graph.graph import build_graph
from src.graph.state import PipelineState


def run_audit(repo_url: str) -> tuple[dict[str, str], PipelineState]:
    """
    Tam audit pipeline'ı çalıştır.

    Args:
        repo_url: GitHub repo URL'si

    Returns:
        (files_dict, final_pipeline_state)
        - files_dict: { "path": "content", ... }
        - final_pipeline_state: tüm agent çıktıları + trace_log

    Raises:
        RuntimeError: Repo erişim hatası
        ValueError:   Dosya bulunamadı veya diğer input hatası
    """

    # ── Step 1: GitHub'dan dosya çek ─────────────────────
    files: dict[str, str] = fetch_target_files(repo_url)

    # ── Step 2: LLM prompt'a hazır format ────────────────
    files_context: str = format_files_context(files)

    # ── Step 3: Pipeline çalıştır ────────────────────────
    pipeline = build_graph()

    initial_state: PipelineState = {
        "files_context":  files_context,
        "analyst_output": "",
        "critic_output":  "",
        "fixer_output":   "",
        "retry_count":    0,
        "approved":       False,
        "trace_log":      [],
    }

    # LangSmith otomatik trace eder (LANGSMITH_API_KEY set ise)
    config = {
        "tags":     ["clean-code-auditor", "multi-agent"],
        "metadata": {"run_type": "audit_pipeline"},
    }

    final_state: PipelineState = pipeline.invoke(initial_state, config=config)

    return files, final_state