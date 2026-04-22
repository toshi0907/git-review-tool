"""cli モジュールのユニットテスト"""
from __future__ import annotations

import pytest

from git_review_tool import cli


class FakeStorage:
    def __init__(self, _db_path: str):
        pass

    def get_or_create_repository_session(self, repository_path: str) -> int:
        assert repository_path == "/repo"
        return 1


class FakeApp:
    def run(self, **_kwargs) -> None:
        pass


def test_auto_detects_base_and_target_from_keyword(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setenv("GIT_REVIEW_TOOL_BASE_BRANCH", "origin/dev")
    monkeypatch.setenv("GIT_REVIEW_TOOL_TARGET_MESSAGE_KEYWORD", "[review]")
    monkeypatch.setattr(
        "sys.argv",
        ["git-review-tool", "--repo", "/repo", "--db", "/repo/.git/review_tool.sqlite3"],
    )
    monkeypatch.setattr(
        cli,
        "resolve_merge_base",
        lambda base_branch, repo_path: "base123"
        if base_branch == "origin/dev" and repo_path == "/repo"
        else "",
    )
    monkeypatch.setattr(
        cli,
        "find_target_commit_by_message",
        lambda base, keyword, repo_path: "target456"
        if base == "base123" and keyword == "[review]" and repo_path == "/repo"
        else "",
    )

    def fake_get_diff(target, repo_path, base=None, encoding=None):
        captured["target"] = target
        captured["repo_path"] = repo_path
        captured["base"] = base
        captured["encoding"] = encoding
        return "diff --git a/a b/a\n@@ -1 +1 @@\n-a\n+b\n"

    monkeypatch.setattr(cli, "get_diff", fake_get_diff)
    monkeypatch.setattr(cli, "parse_diff", lambda _text: [{"file_path": "a", "hunks": [{"body_lines": ["+b"]}]}])
    monkeypatch.setattr(cli, "compute_hunk_hash", lambda _path, _lines: "hunkhash")
    monkeypatch.setattr(cli, "Storage", FakeStorage)
    monkeypatch.setattr(cli, "create_app", lambda **_kwargs: FakeApp())

    cli.main()

    assert captured == {
        "target": "target456",
        "repo_path": "/repo",
        "base": "base123",
        "encoding": None,
    }


def test_target_keyword_without_base_raises_error(monkeypatch):
    monkeypatch.delenv("GIT_REVIEW_TOOL_BASE_BRANCH", raising=False)
    monkeypatch.delenv("GIT_REVIEW_TOOL_TARGET_MESSAGE_KEYWORD", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["git-review-tool", "--repo", "/repo", "--target-message-keyword", "[review]"],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 2
