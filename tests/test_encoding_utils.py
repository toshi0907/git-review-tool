"""encoding_utils モジュールのユニットテスト"""
from __future__ import annotations

import pytest

from git_review_tool.encoding_utils import detect_and_decode


class TestDetectAndDecode:
    def test_utf8_bytes_decoded_correctly(self):
        text = "UTF-8のテキスト"
        assert detect_and_decode(text.encode("utf-8")) == text

    def test_euc_jp_bytes_decoded_correctly(self):
        text = "EUC-JPのテキスト"
        assert detect_and_decode(text.encode("euc-jp")) == text

    def test_shift_jis_bytes_decoded_correctly(self):
        text = "Shift_JISのテキスト"
        # CP932 は Shift_JIS の上位互換のため CP932 エンコードで試みる
        assert detect_and_decode(text.encode("cp932")) == text

    def test_cp932_bytes_decoded_correctly(self):
        text = "CP932のテキスト"
        assert detect_and_decode(text.encode("cp932")) == text

    def test_ascii_bytes_decoded_as_utf8(self):
        text = "hello world"
        assert detect_and_decode(text.encode("ascii")) == text

    def test_latin1_fallback_for_unknown_encoding(self):
        # latin-1 フォールバックで損なわれないことを確認
        data = bytes(range(0x80, 0x100))
        result = detect_and_decode(data)
        # latin-1 でデコードされた結果は再エンコードで元に戻る
        assert result.encode("latin-1") == data

    def test_mixed_utf8_ascii_diff(self):
        """git diff の典型的な出力（ASCII ヘッダ + UTF-8 本文）"""
        header = b"diff --git a/file.py b/file.py\n+++ b/file.py\n"
        body = "日本語コメント\n".encode("utf-8")
        assert detect_and_decode(header + body) == (header + body).decode("utf-8")

    def test_mixed_ascii_euc_jp_diff(self):
        """ASCII ヘッダ + EUC-JP 本文の混在差分"""
        header = b"diff --git a/file.c b/file.c\n+++ b/file.c\n"
        body = "/* EUC-JPコメント */\n".encode("euc-jp")
        result = detect_and_decode(header + body)
        # EUC-JP でデコードされた結果を確認
        assert result == (header + body).decode("euc-jp")
