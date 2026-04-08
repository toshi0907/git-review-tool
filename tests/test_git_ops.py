"""git_ops モジュールのユニットテスト"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from git_review_tool.git_ops import get_diff


class TestGetDiff:
    def test_single_commit_uses_git_show(self, monkeypatch):
        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return SimpleNamespace(returncode=0, stdout="diff", stderr="")

        monkeypatch.setattr("subprocess.run", fake_run)

        out = get_diff("deadbeef", repo_path="/repo")

        assert out == "diff"
        assert captured["cmd"][:4] == ["git", "-C", "/repo", "show"]
        assert "deadbeef" in captured["cmd"]

    def test_two_commit_mode_uses_git_diff(self, monkeypatch):
        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return SimpleNamespace(returncode=0, stdout="diff", stderr="")

        monkeypatch.setattr("subprocess.run", fake_run)

        out = get_diff("target", repo_path="/repo", base="base")

        assert out == "diff"
        assert captured["cmd"][:4] == ["git", "-C", "/repo", "diff"]
        assert "base" in captured["cmd"]
        assert "target" in captured["cmd"]

    def test_raises_when_git_command_fails(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=1, stdout="", stderr="fatal: bad revision")

        monkeypatch.setattr("subprocess.run", fake_run)

        with pytest.raises(ValueError):
            get_diff("bad", repo_path="/repo")
