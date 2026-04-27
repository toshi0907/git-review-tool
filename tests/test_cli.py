"""CLIのレビュー対象自動検出（base/キーワード）周りを検証するテスト。"""
from __future__ import annotations

import pytest

from git_review_tool import cli


class FakeStorage:
    def __init__(self, _db_path: str):
        self._reviewed: dict[str, bool] = {}
        self._session_id = 1

    def get_or_create_repository_session(self, repository_path: str) -> int:
        if repository_path != "/repo":
            raise AssertionError(f"unexpected repository_path: {repository_path}")
        return self._session_id

    def get_reviewed_batch(
        self, hunk_hashes: list[str], session_id: int = 0
    ) -> dict[str, bool]:
        return {h: self._reviewed.get(h, False) for h in hunk_hashes if h in self._reviewed}


class FakeStorageAllReviewed(FakeStorage):
    def get_reviewed_batch(
        self, hunk_hashes: list[str], session_id: int = 0
    ) -> dict[str, bool]:
        return {h: True for h in hunk_hashes}


class FakeApp:
    def run(self, **_kwargs) -> None:
        pass


def test_auto_detects_base_and_target_from_keyword(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setenv("GIT_REVIEW_TOOL_AUTO_BASE_BRANCH", "origin/dev")
    monkeypatch.setenv("GIT_REVIEW_TOOL_AUTO_TARGET_MSG_KWD", "[review]")
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
    monkeypatch.delenv("GIT_REVIEW_TOOL_AUTO_BASE_BRANCH", raising=False)
    monkeypatch.delenv("GIT_REVIEW_TOOL_AUTO_TARGET_MSG_KWD", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["git-review-tool", "--repo", "/repo", "--target-message-keyword", "[review]"],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 2


# ── check_main tests ────────────────────────────────────────────────────────


def _patch_check_common(monkeypatch, diff_text: str, hunk_hash: str = "abc123"):
    """check_main のテストで使う共通パッチ。"""
    monkeypatch.delenv("GIT_REVIEW_TOOL_AUTO_BASE_BRANCH", raising=False)
    monkeypatch.delenv("GIT_REVIEW_TOOL_AUTO_TARGET_MSG_KWD", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["git-review-tool-check", "target456", "--repo", "/repo", "--db", "/tmp/test.sqlite3"],
    )
    monkeypatch.setattr(cli, "get_diff", lambda *_a, **_kw: diff_text)
    monkeypatch.setattr(
        cli,
        "parse_diff",
        lambda _text: [{"file_path": "a", "hunks": [{"body_lines": ["+b"]}]}],
    )
    monkeypatch.setattr(cli, "compute_hunk_hash", lambda _path, _lines: hunk_hash)


def test_check_main_all_reviewed_exits_0(monkeypatch):
    _patch_check_common(monkeypatch, "diff --git a/a b/a\n@@ -1 +1 @@\n-a\n+b\n")
    monkeypatch.setattr(cli, "Storage", FakeStorageAllReviewed)

    with pytest.raises(SystemExit) as exc_info:
        cli.check_main()

    assert exc_info.value.code == 0


def test_check_main_unreviewed_exits_1(monkeypatch):
    _patch_check_common(monkeypatch, "diff --git a/a b/a\n@@ -1 +1 @@\n-a\n+b\n")
    monkeypatch.setattr(cli, "Storage", FakeStorage)

    with pytest.raises(SystemExit) as exc_info:
        cli.check_main()

    assert exc_info.value.code == 1


def test_check_main_empty_diff_exits_0(monkeypatch):
    monkeypatch.delenv("GIT_REVIEW_TOOL_AUTO_BASE_BRANCH", raising=False)
    monkeypatch.delenv("GIT_REVIEW_TOOL_AUTO_TARGET_MSG_KWD", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["git-review-tool-check", "target456", "--repo", "/repo", "--db", "/tmp/test.sqlite3"],
    )
    monkeypatch.setattr(cli, "get_diff", lambda *_a, **_kw: "   ")

    with pytest.raises(SystemExit) as exc_info:
        cli.check_main()

    assert exc_info.value.code == 0


def test_check_main_prints_summary_when_all_reviewed(monkeypatch, capsys):
    _patch_check_common(monkeypatch, "diff --git a/a b/a\n@@ -1 +1 @@\n-a\n+b\n", "abc123def456")
    monkeypatch.setattr(cli, "Storage", FakeStorageAllReviewed)

    with pytest.raises(SystemExit):
        cli.check_main()

    out = capsys.readouterr().out
    assert "1 hunk" in out
    assert "完了" in out


def test_check_main_prints_unreviewed_hashes(monkeypatch, capsys):
    _patch_check_common(monkeypatch, "diff --git a/a b/a\n@@ -1 +1 @@\n-a\n+b\n", "abc123def456")
    monkeypatch.setattr(cli, "Storage", FakeStorage)

    with pytest.raises(SystemExit):
        cli.check_main()

    out = capsys.readouterr().out
    assert "abc123def4" in out
    assert "未レビュー" in out


def test_check_main_no_commit_raises_error(monkeypatch):
    monkeypatch.delenv("GIT_REVIEW_TOOL_AUTO_BASE_BRANCH", raising=False)
    monkeypatch.delenv("GIT_REVIEW_TOOL_AUTO_TARGET_MSG_KWD", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["git-review-tool-check", "--repo", "/repo", "--db", "/tmp/test.sqlite3"],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.check_main()

    assert exc_info.value.code == 2

