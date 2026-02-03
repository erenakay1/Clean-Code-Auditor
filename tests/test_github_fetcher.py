"""
test_github_fetcher.py
──────────────────────
GitHub fetcher'ın URL parsing ve file filtering logic'ini test eder.
(GitHub API call'ları mock edilir — real API çağrısı yapılmaz.)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.api.github_fetcher import parse_repo_url, _is_target_file, format_files_context


# ─── parse_repo_url tests ────────────────────────────────
class TestParseRepoUrl:

    def test_valid_url(self):
        owner, repo = parse_repo_url("https://github.com/myuser/myrepo")
        assert owner == "myuser"
        assert repo  == "myrepo"

    def test_trailing_slash(self):
        owner, repo = parse_repo_url("https://github.com/user/repo/")
        assert owner == "user"
        assert repo  == "repo"

    def test_git_suffix(self):
        owner, repo = parse_repo_url("https://github.com/user/repo.git")
        assert owner == "user"
        assert repo  == "repo"

    def test_trailing_slash_and_git(self):
        owner, repo = parse_repo_url("https://github.com/user/repo.git/")
        assert owner == "user"
        assert repo  == "repo"

    def test_invalid_url_no_repo(self):
        with pytest.raises(ValueError, match="Gecersiz"):
            parse_repo_url("https://github.com/onlyuser")

    def test_invalid_url_empty(self):
        with pytest.raises(ValueError, match="Gecersiz"):
            parse_repo_url("")

    def test_invalid_url_extra_path(self):
        with pytest.raises(ValueError, match="Gecersiz"):
            parse_repo_url("https://github.com/user/repo/tree/main")


# ─── _is_target_file tests ───────────────────────────────
class TestIsTargetFile:

    def test_cs_file(self):
        assert _is_target_file("Program.cs") is True

    def test_csproj_file(self):
        assert _is_target_file("MyApp.csproj") is True

    def test_case_insensitive(self):
        assert _is_target_file("SERVICE.CS") is True
        assert _is_target_file("App.CsProj") is True

    def test_non_target_extension(self):
        assert _is_target_file("readme.md")     is False
        assert _is_target_file("app.py")        is False
        assert _is_target_file("style.css")     is False

    def test_no_extension(self):
        assert _is_target_file("Dockerfile") is False


# ─── format_files_context tests ──────────────────────────
class TestFormatFilesContext:

    def test_format_single_file(self):
        files = {"src/Program.cs": "using System;"}
        result = format_files_context(files)
        assert "=== FILE: src/Program.cs ===" in result
        assert "using System;" in result

    def test_format_multiple_files(self):
        files = {
            "Program.cs": "content_a",
            "App.csproj": "content_b",
        }
        result = format_files_context(files)
        assert "=== FILE: Program.cs ===" in result
        assert "=== FILE: App.csproj ===" in result

    def test_format_empty(self):
        result = format_files_context({})
        assert result == ""