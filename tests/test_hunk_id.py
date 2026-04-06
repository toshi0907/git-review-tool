"""hunk_id モジュールのユニットテスト"""
from __future__ import annotations

import hashlib

from git_review_tool.hunk_id import compute_hunk_hash


class TestComputeHunkHash:
    def test_returns_string(self):
        result = compute_hunk_hash("foo.py", ["+added", "-removed"])
        assert isinstance(result, str)

    def test_returns_sha256_hex(self):
        result = compute_hunk_hash("foo.py", ["+added"])
        # SHA256 は 64 文字の16進数
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        a = compute_hunk_hash("foo.py", ["+line1", "-line2"])
        b = compute_hunk_hash("foo.py", ["+line1", "-line2"])
        assert a == b

    def test_different_file_path_differs(self):
        a = compute_hunk_hash("foo.py", ["+line1"])
        b = compute_hunk_hash("bar.py", ["+line1"])
        assert a != b

    def test_different_body_differs(self):
        a = compute_hunk_hash("foo.py", ["+line1"])
        b = compute_hunk_hash("foo.py", ["+line2"])
        assert a != b

    def test_different_order_differs(self):
        a = compute_hunk_hash("foo.py", ["+line1", "+line2"])
        b = compute_hunk_hash("foo.py", ["+line2", "+line1"])
        assert a != b

    def test_empty_body_lines(self):
        result = compute_hunk_hash("foo.py", [])
        assert len(result) == 64

    def test_matches_manual_sha256(self):
        file_path = "src/main.py"
        body_lines = ["+added line", "-removed line", " context"]
        content = file_path + "\n" + "\n".join(body_lines)
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert compute_hunk_hash(file_path, body_lines) == expected

    def test_unicode_content(self):
        result = compute_hunk_hash("ファイル.py", ["+追加行", "-削除行"])
        assert len(result) == 64
