"""diff_parser モジュールのユニットテスト"""
from __future__ import annotations

import pytest
from git_review_tool.diff_parser import parse_diff


SIMPLE_DIFF = """\
diff --git a/foo.py b/foo.py
index 0000000..1111111 100644
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,4 @@
 line1
-line2
+line2 modified
+line2b
 line3
"""

MULTI_FILE_DIFF = """\
diff --git a/foo.py b/foo.py
index 0000000..1111111 100644
--- a/foo.py
+++ b/foo.py
@@ -1,2 +1,2 @@
-old foo
+new foo
diff --git a/bar.py b/bar.py
index 2222222..3333333 100644
--- a/bar.py
+++ b/bar.py
@@ -5,3 +5,2 @@
 ctx
-removed
 end
"""

MULTI_HUNK_DIFF = """\
diff --git a/baz.py b/baz.py
index 4444444..5555555 100644
--- a/baz.py
+++ b/baz.py
@@ -1,3 +1,3 @@
 a
-b
+B
 c
@@ -10,3 +10,3 @@
 x
-y
+Y
 z
"""

BINARY_DIFF = """\
diff --git a/image.png b/image.png
index 0000000..1111111 100644
Binary files a/image.png and b/image.png differ
"""

DELETED_FILE_DIFF = """\
diff --git a/gone.py b/gone.py
deleted file mode 100644
index 0000000..1111111
--- a/gone.py
+++ /dev/null
@@ -1,2 +0,0 @@
-line1
-line2
"""


class TestParseDiffBasic:
    def test_returns_list(self):
        result = parse_diff(SIMPLE_DIFF)
        assert isinstance(result, list)

    def test_single_file_count(self):
        result = parse_diff(SIMPLE_DIFF)
        assert len(result) == 1

    def test_file_path(self):
        result = parse_diff(SIMPLE_DIFF)
        assert result[0]["file_path"] == "foo.py"

    def test_hunk_count(self):
        result = parse_diff(SIMPLE_DIFF)
        assert len(result[0]["hunks"]) == 1

    def test_hunk_header(self):
        hunk = parse_diff(SIMPLE_DIFF)[0]["hunks"][0]
        assert hunk["header"].startswith("@@ -1,3 +1,4 @@")

    def test_body_lines_include_added(self):
        hunk = parse_diff(SIMPLE_DIFF)[0]["hunks"][0]
        assert "+line2 modified" in hunk["body_lines"]
        assert "+line2b" in hunk["body_lines"]

    def test_body_lines_include_removed(self):
        hunk = parse_diff(SIMPLE_DIFF)[0]["hunks"][0]
        assert "-line2" in hunk["body_lines"]

    def test_body_lines_include_context(self):
        hunk = parse_diff(SIMPLE_DIFF)[0]["hunks"][0]
        assert " line1" in hunk["body_lines"]

    def test_hunk_hash_present(self):
        hunk = parse_diff(SIMPLE_DIFF)[0]["hunks"][0]
        # hash はデフォルト空文字（cli.py で後から付与される）
        assert "hunk_hash" in hunk


class TestParseDiffMultiFile:
    def test_two_files(self):
        result = parse_diff(MULTI_FILE_DIFF)
        assert len(result) == 2

    def test_file_paths(self):
        result = parse_diff(MULTI_FILE_DIFF)
        paths = [f["file_path"] for f in result]
        assert "foo.py" in paths
        assert "bar.py" in paths


class TestParseDiffMultiHunk:
    def test_two_hunks_in_one_file(self):
        result = parse_diff(MULTI_HUNK_DIFF)
        assert len(result) == 1
        assert len(result[0]["hunks"]) == 2

    def test_hunk_headers_differ(self):
        hunks = parse_diff(MULTI_HUNK_DIFF)[0]["hunks"]
        assert hunks[0]["header"] != hunks[1]["header"]


class TestParseDiffEdgeCases:
    def test_empty_diff(self):
        result = parse_diff("")
        assert result == []

    def test_binary_file_excluded(self):
        # バイナリファイルは hunk がないので除外される
        result = parse_diff(BINARY_DIFF)
        assert result == []

    def test_deleted_file(self):
        result = parse_diff(DELETED_FILE_DIFF)
        assert len(result) == 1
        assert result[0]["file_path"] == "/dev/null"

    def test_diff_with_only_header_no_hunks(self):
        diff = "diff --git a/README.md b/README.md\n"
        result = parse_diff(diff)
        assert result == []
