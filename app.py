"""
app.py — Streamlit Entry Point
───────────────────────────────
Clean Code Auditor ana arayüzü.

Imports src/ modulerini kullanır.
"""

import os
import sys
import json

import streamlit as st

# ── src/ import path ─────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from src.core.config import settings
from src.api.github_fetcher import parse_repo_url
from src.services.audit_service import run_audit
from src.utils.parser import safe_json_parse


# ═══════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="🔍 Clean Code Auditor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ═══════════════════════════════════════════════════════════
#  CUSTOM CSS
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
    .stApp { background-color: #0f1117; color: #e2e8f0; }

    /* ── Agent Status Cards ─────────────────────────── */
    .agent-card {
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 12px;
        border-left: 4px solid;
    }
    .agent-card.pending   { background:#1a1d26; border-color:#4a5568; }
    .agent-card.running   { background:#1e2538; border-color:#f6ad55; }
    .agent-card.done      { background:#1a2e2a; border-color:#48bb78; }

    .agent-card h4       { margin:0 0 6px; font-size:1rem; }
    .agent-card .badge   { font-size:0.72rem; padding:2px 10px; border-radius:20px; }
    .badge-pending       { background:#2d3748; color:#a0aec0; }
    .badge-running       { background:#2c2415; color:#f6ad55; }
    .badge-done          { background:#1c3a2e; color:#48bb78; }

    /* ── Severity Colors ─────────────────────────────── */
    .sev-critical { color:#fc8181; font-weight:600; }
    .sev-warning  { color:#f6ad55; font-weight:600; }
    .sev-info     { color:#63b3ed; font-weight:600; }

    /* ── Trace Box ───────────────────────────────────── */
    .trace-box {
        background:#1a1d26; border:1px solid #2d3748;
        border-radius:10px; padding:16px 20px; margin-top:18px;
    }
    .trace-box a { color:#63b3ed; text-decoration:none; font-weight:600; }
    .trace-box a:hover { text-decoration:underline; }

    /* ── Button ──────────────────────────────────────── */
    div.stButton button {
        background:#3182ce; color:#fff; border:none;
        border-radius:8px; padding:10px 28px;
        font-size:1rem; cursor:pointer; width:100%;
    }
    div.stButton button:hover { background:#2b6cb0; }

    /* ── Hero ────────────────────────────────────────── */
    .hero-title { font-size:2rem; font-weight:700; margin-bottom:4px; }
    .hero-sub   { color:#718096; font-size:0.95rem; margin-bottom:24px; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  HELPER: Agent Card HTML
# ═══════════════════════════════════════════════════════════
_STATUS_LABELS = {
    "pending": ("⏳ Bekliyor",   "badge-pending"),
    "running": ("⚡ Çalışıyor",  "badge-running"),
    "done":    ("✅ Tamamlandı", "badge-done"),
}

def _agent_card_html(name: str, status: str, detail: str = "") -> str:
    label, badge_cls = _STATUS_LABELS.get(status, _STATUS_LABELS["pending"])
    detail_html = (
        f'<p style="color:#a0aec0;margin:4px 0 0;font-size:0.85rem;">{detail}</p>'
        if detail else ""
    )
    return (
        f'<div class="agent-card {status}">'
        f'  <h4>🤖 {name} <span class="badge {badge_cls}">{label}</span></h4>'
        f'  {detail_html}'
        f'</div>'
    )


# ═══════════════════════════════════════════════════════════
#  SIDEBAR — env check
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Configuration")
    st.checkbox(
        "OpenAI Key ✓" if settings.openai_ok else "❌ OpenAI Key eksik",
        value=settings.openai_ok, disabled=True,
    )
    st.checkbox(
        "LangSmith Key ✓" if settings.langsmith_ok else "❌ LangSmith Key eksik",
        value=settings.langsmith_ok, disabled=True,
    )
    st.checkbox(
        "GitHub Token ✓" if settings.github_token_ok else "GitHub Token (optional)",
        value=settings.github_token_ok, disabled=True,
    )
    st.divider()
    st.caption(f"LangSmith project: `{settings.LANGSMITH_PROJECT}`")


# ═══════════════════════════════════════════════════════════
#  HERO + INPUT
# ═══════════════════════════════════════════════════════════
st.markdown('<div class="hero-title">🔍 Autonomous Clean Code Auditor</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Multi-Agent .NET / SOLID Code Analysis · LangSmith Traced</div>', unsafe_allow_html=True)

col_input, col_btn = st.columns([3, 1])
repo_url   = col_input.text_input(
    "GitHub Repo URL",
    placeholder="https://github.com/user/repo",
    label_visibility="collapsed",
)
run_clicked = col_btn.button("🚀 Analiz Başlat")


# ═══════════════════════════════════════════════════════════
#  MAIN LOGIC
# ═══════════════════════════════════════════════════════════
if run_clicked:

    # ── Validation ─────────────────────────────────────
    if not repo_url.strip():
        st.error("⚠️ Lütfen bir GitHub repo URL'si girin.")
        st.stop()

    try:
        parse_repo_url(repo_url)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    if not settings.openai_ok or not settings.langsmith_ok:
        st.error("❌ .env'de OPENAI_API_KEY ve LANGSMITH_API_KEY tanımlanmalı.")
        st.stop()

    # ── Agent progress placeholders ────────────────────
    st.divider()
    st.subheader("🤖 Agent Pipeline")

    ph_analyst = st.empty()
    ph_critic  = st.empty()
    ph_fixer   = st.empty()

    # initial state → Analyst running, diğerleri pending
    ph_analyst.markdown(_agent_card_html("Agent A — Analyst", "running", "Kodu analiz ediyor..."), unsafe_allow_html=True)
    ph_critic.markdown(_agent_card_html("Agent B — Critic",  "pending"), unsafe_allow_html=True)
    ph_fixer.markdown(_agent_card_html("Agent C — Fixer",   "pending"), unsafe_allow_html=True)

    # ── Run audit ──────────────────────────────────────
    with st.status("Pipeline çalışıyor...", expanded=True) as pipe_status:
        try:
            files, final_state = run_audit(repo_url)
            pipe_status.update(label="✅ Pipeline tamamlandı.", state="complete")
        except (RuntimeError, ValueError) as e:
            pipe_status.update(label=f"❌ Hata: {e}", state="error")
            st.error(str(e))
            st.stop()
        except Exception as e:
            pipe_status.update(label=f"❌ Beklenmeyen hata: {e}", state="error")
            st.error(str(e))
            st.stop()

    # ── Parse agent outputs ────────────────────────────
    analyst_data = safe_json_parse(final_state["analyst_output"])
    critic_data  = safe_json_parse(final_state["critic_output"])
    fixer_data   = safe_json_parse(final_state["fixer_output"])

    analyst_count = len(analyst_data.get("analyst_findings", []))
    critic_missed = len(critic_data.get("critic_review", {}).get("missed_issues", []))
    fixer_count   = len(fixer_data.get("fixes", []))

    # ── Update cards → done ────────────────────────────
    ph_analyst.markdown(_agent_card_html("Agent A — Analyst", "done", f"{analyst_count} sorun tespit etti"), unsafe_allow_html=True)
    ph_critic.markdown(_agent_card_html("Agent B — Critic",  "done", f"{critic_missed} eksik bulduktan sonra onayladı"), unsafe_allow_html=True)
    ph_fixer.markdown(_agent_card_html("Agent C — Fixer",   "done", f"{fixer_count} düzeltme üretildi"), unsafe_allow_html=True)

    # ── Fetched files expander ─────────────────────────
    with st.expander(f"📁 Çekilen Dosyalar ({len(files)})"):
        for path, content in files.items():
            st.markdown(f"`{path}` — {len(content)} char")

    # ═══════════════════════════════════════════════════
    #  RESULT TABS
    # ═══════════════════════════════════════════════════
    st.divider()
    tab_analyst, tab_critic, tab_fixer, tab_trace = st.tabs([
        "📊 Analyst Bulguları",
        "🔎 Critic Denetim",
        "🔧 Fixer Düzeltmeler",
        "🔗 LangSmith Trace",
    ])

    # ─── TAB: Analyst ────────────────────────────────
    with tab_analyst:
        findings = analyst_data.get("analyst_findings", [])
        summary  = analyst_data.get("summary", "")

        if summary:
            st.info(f"📝 Özet: {summary}")

        if not findings:
            st.success("🎉 Sorun bulunamadı!")
        else:
            sev_class = {"Critical": "sev-critical", "Warning": "sev-warning", "Info": "sev-info"}

            for sev in ["Critical", "Warning", "Info"]:
                group = [f for f in findings if f.get("severity") == sev]
                if not group:
                    continue

                st.markdown(
                    f"### <span class='{sev_class[sev]}'>{sev} ({len(group)})</span>",
                    unsafe_allow_html=True,
                )
                for item in group:
                    with st.expander(f"📄 {item.get('file', '')} → {item.get('line_hint', '')}"):
                        st.markdown(f"**Kategori:** `{item.get('category', '')}`")
                        st.markdown(f"**Sorun:** {item.get('description', '')}")
                        st.markdown(f"**Öneri:** {item.get('suggestion', '')}")

    # ─── TAB: Critic ─────────────────────────────────
    with tab_critic:
        review      = critic_data.get("critic_review", {})
        approved    = review.get("approved", False)
        feedback    = review.get("feedback", "")
        missed      = review.get("missed_issues", [])
        corrections = review.get("corrections", [])

        st.markdown(
            f"**Onay Durumu:** {'✅ Onaylandı' if approved else '⚠️ Onaylanmadı (retry sonrası devam etti)'}"
        )

        if feedback:
            st.info(f"💬 Critic Geri Bildirim:\n> {feedback}")

        if missed:
            st.markdown("#### 🔍 Analyst'in Atladığı Sorunlar")
            for item in missed:
                with st.expander(f"📄 {item.get('file', '')} → {item.get('line_hint', '')}"):
                    st.markdown(f"**Severity:** `{item.get('severity', '')}`")
                    st.markdown(f"**Sorun:** {item.get('description', '')}")
                    st.markdown(f"**Öneri:** {item.get('suggestion', '')}")

        if corrections:
            st.markdown("#### ✏️ Düzeltmeler")
            for c in corrections:
                st.markdown(f"> Finding #{c.get('original_finding_index', '')} → {c.get('correction', '')}")

    # ─── TAB: Fixer ──────────────────────────────────
    with tab_fixer:
        fixes        = fixer_data.get("fixes", [])
        refactor_sum = fixer_data.get("refactor_summary", "")

        if refactor_sum:
            st.info(f"📝 Refactor Özeti: {refactor_sum}")

        if not fixes:
            st.success("🎉 Düzeltme yapılmasına gerek yok!")
        else:
            for i, fix in enumerate(fixes, 1):
                with st.expander(f"🔧 Fix #{i} — {fix.get('file', '')} | {fix.get('issue_category', '')}"):
                    st.markdown(f"**Açıklama:** {fix.get('explanation', '')}")

                    col_orig, col_fixed = st.columns(2)

                    col_orig.markdown("##### ❌ Orijinal")
                    col_orig.code(fix.get("original_code", ""), language="csharp")

                    col_fixed.markdown("##### ✅ Düzeltilmiş")
                    col_fixed.code(fix.get("fixed_code", ""), language="csharp")

    # ─── TAB: LangSmith Trace ────────────────────────
    with tab_trace:
        project = settings.LANGSMITH_PROJECT

        st.markdown(f"""
        <div class="trace-box">
            <h4>🔗 LangSmith Trace — Teknik Kanıt</h4>
            <p style="color:#a0aec0; margin:8px 0;">
                Tüm agent etkileşimleri (debate) LangSmith'te kaydedildi.
            </p>
            <a href="https://smith.langchain.com" target="_blank">
                👉 LangSmith Dashboard → Proje: <code>{project}</code>
            </a>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.markdown("#### 📋 Agent Debate Log")

        for entry in final_state.get("trace_log", []):
            agent   = entry.get("agent", "?")
            step    = entry.get("step", "?")
            detail  = {k: v for k, v in entry.items() if k not in ("agent", "step")}
            st.markdown(f"- **[{agent}]** `{step}` → {detail}")