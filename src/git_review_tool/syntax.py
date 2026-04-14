"""シンタックスハイライト処理（Pygments を使用）"""
from __future__ import annotations

import re
from typing import TypedDict

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_for_filename
from pygments.util import ClassNotFound


class HighlightedLine(TypedDict):
    type: str    # "add" | "del" | "ctx"
    prefix: str  # "+" | "-" | " "
    html: str    # ハイライト済みHTMLコード（プレフィックスは含まない）


_FORMATTER = HtmlFormatter(nowrap=True)


def get_pygments_css() -> str:
    """diff 表示に適用する Pygments の CSS を返す。"""
    return HtmlFormatter(style="default").get_style_defs(".diff")


def _split_highlighted_lines(html: str) -> list[str]:
    """ハイライト済みHTMLを、スパンをまたぐ場合も考慮して行単位に分割する。

    Pygments の出力には改行をまたぐスパンが含まれることがある。
    各行の末尾で未閉じのスパンを閉じ、次の行の先頭で再度開くことで
    各行が独立した有効なHTMLになるようにする。
    """
    result: list[str] = []
    current_line: list[str] = []
    open_spans: list[str] = []  # 現在開いているスパンタグのスタック

    for token in re.split(r"(<[^>]+>)", html):
        if re.match(r"<span", token):
            open_spans.append(token)
            current_line.append(token)
        elif token == "</span>":
            if open_spans:
                open_spans.pop()
            current_line.append(token)
        elif token.startswith("<"):
            # その他のタグ（nowrap=True の出力には通常含まれないが念のため）
            current_line.append(token)
        else:
            # テキスト（改行を含む可能性あり）
            lines = token.split("\n")
            for i, part in enumerate(lines):
                if i > 0:
                    # 前の行の未閉じスパンを閉じる
                    current_line.extend(["</span>"] * len(open_spans))
                    result.append("".join(current_line))
                    # 新しい行でスパンを再度開く
                    current_line = list(open_spans)
                current_line.append(part)

    if current_line:
        result.append("".join(current_line))

    return result


def highlight_diff_lines(
    body_lines: list[str],
    file_path: str,
) -> list[HighlightedLine]:
    """差分行にシンタックスハイライトを適用する。

    コードブロック全体をまとめてハイライトすることで、
    マルチライン構造（複数行コメントなど）も正しく扱う。

    Args:
        body_lines: diff 本文行のリスト（各行は +/-/スペース で始まる）
        file_path: ファイルパス（言語判定に使用）

    Returns:
        HighlightedLine のリスト
    """
    if not body_lines:
        return []

    # diff プレフィックス（+/-/スペース）を取り除いてコードを結合
    code_lines = [line[1:] if line else "" for line in body_lines]
    code = "\n".join(code_lines)

    # ファイル拡張子から言語を判定（失敗時は TextLexer でハイライトなし）
    try:
        lexer = get_lexer_for_filename(file_path, code, stripall=False)
    except ClassNotFound:
        lexer = TextLexer()

    # ハイライト実行
    highlighted_html = highlight(code, lexer, _FORMATTER)

    # 行単位に分割（スパンの整合性を維持しながら）
    hl_lines = _split_highlighted_lines(highlighted_html)

    # 行数が足りない場合は空文字で埋める。
    # Pygments が行数を増やす場合（末尾に余分な行を追加するなど）は、
    # enumerate(body_lines) のループが自然に body_lines の範囲で止まるため
    # 余分な行は無視される。
    while len(hl_lines) < len(body_lines):
        hl_lines.append("")

    # 各行に diff タイプとプレフィックスを付与して返す
    result: list[HighlightedLine] = []
    for i, original_line in enumerate(body_lines):
        prefix = original_line[0] if original_line else " "
        if prefix == "+":
            line_type = "add"
        elif prefix == "-":
            line_type = "del"
        else:
            line_type = "ctx"
        result.append(
            HighlightedLine(
                type=line_type,
                prefix=prefix,
                html=hl_lines[i] if i < len(hl_lines) else "",
            )
        )

    return result
