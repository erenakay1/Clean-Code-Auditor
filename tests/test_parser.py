"""
test_parser.py
──────────────
utils/parser.py'nin safe_json_parse ve merge_issues'ı test eder.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from src.utils.parser import safe_json_parse, merge_issues


# ─── safe_json_parse tests ───────────────────────────────
class TestSafeJsonParse:

    def test_plain_json(self):
        raw = '{"key": "value"}'
        assert safe_json_parse(raw) == {"key": "value"}

    def test_markdown_json_block(self):
        raw = '```json\n{"key": "value"}\n```'
        assert safe_json_parse(raw) == {"key": "value"}

    def test_markdown_block_no_json_label(self):
        raw = '```\n{"key": "value"}\n```'
        assert safe_json_parse(raw) == {"key": "value"}

    def test_with_whitespace(self):
        raw = '  \n  {"key": "value"}  \n  '
        assert safe_json_parse(raw) == {"key": "value"}

    def test_nested_json(self):
        data = {"findings": [{"file": "A.cs", "severity": "Critical"}]}
        raw  = json.dumps(data)
        assert safe_json_parse(raw) == data

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="JSON parse hatası"):
            safe_json_parse("this is not json at all")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            safe_json_parse("")


# ─── merge_issues tests ──────────────────────────────────
class TestMergeIssues:

    def _make_analyst(self, findings: list) -> str:
        return json.dumps({"analyst_findings": findings})

    def _make_critic(self, missed: list) -> str:
        return json.dumps({"critic_review": {"missed_issues": missed}})

    def test_merge_both(self):
        analyst = self._make_analyst([{"file": "A.cs", "severity": "Critical"}])
        critic  = self._make_critic([{"file": "B.cs", "severity": "Warning"}])

        result = merge_issues(analyst, critic)

        assert len(result) == 2
        assert result[0]["file"] == "A.cs"
        assert result[1]["file"] == "B.cs"

    def test_merge_only_analyst(self):
        analyst = self._make_analyst([{"file": "A.cs"}])
        critic  = self._make_critic([])

        result = merge_issues(analyst, critic)
        assert len(result) == 1

    def test_merge_only_critic(self):
        analyst = self._make_analyst([])
        critic  = self._make_critic([{"file": "B.cs"}])

        result = merge_issues(analyst, critic)
        assert len(result) == 1

    def test_merge_empty_both(self):
        analyst = self._make_analyst([])
        critic  = self._make_critic([])

        result = merge_issues(analyst, critic)
        assert result == []