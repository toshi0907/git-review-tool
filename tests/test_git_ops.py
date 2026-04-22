"""git_ops モジュールのユニットテスト"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from git_review_tool.git_ops import (
    find_target_commit_by_message,
    get_diff,
    resolve_merge_base,
)


class TestGetDiff:
    def test_single_commit_uses_git_show(self, monkeypatch):
        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return SimpleNamespace(returncode=0, stdout=b"diff", stderr=b"")

        monkeypatch.setattr("subprocess.run", fake_run)

        out = get_diff("deadbeef", repo_path="/repo")

        assert out == "diff"
        assert captured["cmd"][:6] == ["git", "-C", "/repo", "-c", "safe.directory=/repo", "show"]
        assert "deadbeef" in captured["cmd"]

    def test_two_commit_mode_uses_git_diff(self, monkeypatch):
        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return SimpleNamespace(returncode=0, stdout=b"diff", stderr=b"")

        monkeypatch.setattr("subprocess.run", fake_run)

        out = get_diff("target", repo_path="/repo", base="base")

        assert out == "diff"
        assert captured["cmd"][:6] == ["git", "-C", "/repo", "-c", "safe.directory=/repo", "diff"]
        assert "base" in captured["cmd"]
        assert "target" in captured["cmd"]

    def test_raises_when_git_command_fails(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            return SimpleNamespace(
                returncode=1, stdout=b"", stderr=b"fatal: bad revision"
            )

        monkeypatch.setattr("subprocess.run", fake_run)

        with pytest.raises(ValueError):
            get_diff("bad", repo_path="/repo")

    def test_euc_jp_diff_is_decoded_correctly(self, monkeypatch):
        """EUC-JPエンコードの差分が文字化けなくデコードされることを確認"""
        euc_jp_text = "テスト用日本語コメント"
        euc_jp_bytes = euc_jp_text.encode("euc-jp")

        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=0, stdout=euc_jp_bytes, stderr=b"")

        monkeypatch.setattr("subprocess.run", fake_run)

        out = get_diff("deadbeef", repo_path="/repo")

        assert out == euc_jp_text

    def test_explicit_encoding_is_used(self, monkeypatch):
        """--encoding オプションで指定したエンコーディングが使われることを確認"""
        euc_jp_text = "明示的EUC-JP指定"
        euc_jp_bytes = euc_jp_text.encode("euc-jp")

        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=0, stdout=euc_jp_bytes, stderr=b"")

        monkeypatch.setattr("subprocess.run", fake_run)

        out = get_diff("deadbeef", repo_path="/repo", encoding="euc-jp")

        assert out == euc_jp_text

    def test_utf8_diff_unchanged(self, monkeypatch):
        """UTF-8の差分が引き続き正常にデコードされることを確認"""
        utf8_text = "UTF-8のコミットメッセージ"
        utf8_bytes = utf8_text.encode("utf-8")

        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=0, stdout=utf8_bytes, stderr=b"")

        monkeypatch.setattr("subprocess.run", fake_run)

        out = get_diff("deadbeef", repo_path="/repo")

        assert out == utf8_text


class TestResolveMergeBase:
    def test_uses_git_merge_base(self, monkeypatch):
        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return SimpleNamespace(returncode=0, stdout="abc123\n", stderr="")

        monkeypatch.setattr("subprocess.run", fake_run)

        out = resolve_merge_base("main", repo_path="/repo")

        assert out == "abc123"
        assert captured["cmd"] == [
            "git",
            "-C",
            "/repo",
            "-c",
            "safe.directory=/repo",
            "merge-base",
            "main",
            "HEAD",
        ]

    def test_raises_when_git_merge_base_fails(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=1, stdout="", stderr="fatal: bad revision")

        monkeypatch.setattr("subprocess.run", fake_run)

        with pytest.raises(ValueError):
            resolve_merge_base("origin/dev", repo_path="/repo")


class TestFindTargetCommitByMessage:
    def test_uses_git_log_with_grep(self, monkeypatch):
        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return SimpleNamespace(returncode=0, stdout="target123\nother456\n", stderr="")

        monkeypatch.setattr("subprocess.run", fake_run)

        out = find_target_commit_by_message(
            base="base123",
            keyword="[review]",
            repo_path="/repo",
        )

        assert out == "target123"
        assert captured["cmd"] == [
            "git",
            "-C",
            "/repo",
            "-c",
            "safe.directory=/repo",
            "log",
            "--format=%H",
            "--fixed-strings",
            "--grep=[review]",
            "base123..HEAD",
        ]

    def test_raises_when_no_matching_commit(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=0, stdout="\n", stderr="")

        monkeypatch.setattr("subprocess.run", fake_run)

        with pytest.raises(ValueError):
            find_target_commit_by_message(
                base="base123",
                keyword="[review]",
                repo_path="/repo",
            )
