"""
parser.py
─────────
LLM çıktılarından JSON parse eden yardımcı functions.
LLM bazen ```json ... ``` block ile döndürür → burada temizlenir.
"""

import json


def safe_json_parse(raw: str) -> dict:
    """
    LLM çıktısından JSON bul ve parse et.

    Handles:
        - ```json ... ``` markdown blocks
        - Leading/trailing whitespace
        - Plain JSON string

    Raises:
        ValueError: parse başarısız olursa
    """
    text = raw.strip()

    # markdown code block varsa çıkar
    if text.startswith("```"):
        parts = text.split("```")
        # parts[0] = "", parts[1] = "json\n{...}", parts[2] = ""
        if len(parts) >= 2:
            inner = parts[1]
            if inner.startswith("json"):
                inner = inner[4:]             # "json" prefix'i kes
            text = inner.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse hatası: {e}\n\nRaw input:\n{raw[:500]}") from e


def merge_issues(analyst_output: str, critic_output: str) -> list[dict]:
    """
    Analyst findings + Critic missed_issues'ı tek listede birleştir.
    Fixer'a verilecek "approved issues" listesi.
    """
    analyst_data = safe_json_parse(analyst_output)
    critic_data  = safe_json_parse(critic_output)

    all_issues = list(analyst_data.get("analyst_findings", []))

    missed = critic_data.get("critic_review", {}).get("missed_issues", [])
    all_issues.extend(missed)

    return all_issues