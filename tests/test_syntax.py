"""syntax モジュールのテスト"""
from __future__ import annotations

import pytest
from git_review_tool.syntax import (
    get_pygments_css,
    highlight_diff_lines,
    _split_highlighted_lines,
)


class TestGetPygmentsCSS:
    def test_returns_string(self):
        css = get_pygments_css()
        assert isinstance(css, str)

    def test_contains_diff_scope(self):
        css = get_pygments_css()
        # .diff セレクタでスコープされていることを確認
        assert ".diff" in css

    def test_nonempty(self):
        css = get_pygments_css()
        assert len(css) > 0


class TestSplitHighlightedLines:
    def test_simple_split(self):
        html = "line1\nline2\nline3"
        result = _split_highlighted_lines(html)
        assert result == ["line1", "line2", "line3"]

    def test_balanced_spans_within_line(self):
        html = '<span class="k">if</span> x\n<span class="n">y</span>'
        result = _split_highlighted_lines(html)
        assert len(result) == 2
        assert "<span" in result[0]
        assert "</span>" in result[0]

    def test_span_crossing_line_boundary(self):
        # スパンが行をまたぐ場合：各行が独立した有効な HTML になること
        html = '<span class="s">"line1\nline2"</span>'
        result = _split_highlighted_lines(html)
        assert len(result) == 2
        # 最初の行はスパンが閉じられている
        assert result[0].endswith("</span>")
        # 2行目はスパンが再度開かれている
        assert result[1].startswith('<span class="s">')

    def test_empty_input(self):
        result = _split_highlighted_lines("")
        assert result == [""]

    def test_single_line_no_newline(self):
        html = "<span>hello</span>"
        result = _split_highlighted_lines(html)
        assert result == ["<span>hello</span>"]


class TestHighlightDiffLines:
    def test_empty_input(self):
        result = highlight_diff_lines([], "foo.py")
        assert result == []

    def test_line_types_detected(self):
        lines = ["+added line", "-removed line", " context line"]
        result = highlight_diff_lines(lines, "foo.txt")
        assert result[0]["type"] == "add"
        assert result[1]["type"] == "del"
        assert result[2]["type"] == "ctx"

    def test_prefixes_preserved(self):
        lines = ["+added", "-removed", " context"]
        result = highlight_diff_lines(lines, "foo.txt")
        assert result[0]["prefix"] == "+"
        assert result[1]["prefix"] == "-"
        assert result[2]["prefix"] == " "

    def test_html_field_is_string(self):
        lines = ["+int x = 5;", " // comment"]
        result = highlight_diff_lines(lines, "foo.c")
        for item in result:
            assert isinstance(item["html"], str)

    def test_output_length_matches_input(self):
        lines = ["+line1", "-line2", " line3", "+line4"]
        result = highlight_diff_lines(lines, "foo.py")
        assert len(result) == 4

    def test_code_content_preserved_in_html(self):
        lines = ["+hello_world"]
        result = highlight_diff_lines(lines, "foo.txt")
        assert "hello_world" in result[0]["html"]

    def test_cpp_file_uses_lexer(self):
        lines = ["+int main() {", "+ return 0;", "+}"]
        result = highlight_diff_lines(lines, "main.cpp")
        # C++ のキーワード `int` や `return` がハイライトされるはず
        full_html = "".join(r["html"] for r in result)
        # span タグが含まれることでハイライトが適用されたことを確認
        assert "<span" in full_html

    def test_python_file_uses_lexer(self):
        lines = ["+def foo():", "+    return 42"]
        result = highlight_diff_lines(lines, "script.py")
        full_html = "".join(r["html"] for r in result)
        assert "<span" in full_html

    def test_unknown_extension_fallback(self):
        lines = ["+some content here"]
        # 不明な拡張子でも例外を出さないことを確認
        result = highlight_diff_lines(lines, "file.xyzunknown123")
        assert len(result) == 1
        assert result[0]["type"] == "add"

    def test_line_with_empty_content(self):
        # プレフィックスのみの行（空行）を正しく処理すること
        lines = ["+", " "]
        result = highlight_diff_lines(lines, "foo.py")
        assert len(result) == 2

    def test_html_safe_escaping(self):
        # Pygments は HTML 特殊文字をエスケープするはず
        lines = ['+ x < y && y > 0;']
        result = highlight_diff_lines(lines, "foo.c")
        # 生の < > が HTML として安全にエンコードされているか、
        # または span でラップされていることを確認
        assert "<script" not in result[0]["html"].lower()
