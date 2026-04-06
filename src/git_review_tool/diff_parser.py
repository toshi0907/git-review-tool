"""unified diff をファイル→hunk に分解する最小パーサー"""
from __future__ import annotations

import re
from typing import TypedDict


class HunkInfo(TypedDict):
    header: str           # @@ ... @@ の行
    body_lines: list[str] # hunk 本文行（header を除く）
    hunk_hash: str        # compute_hunk_hash で後から付与


class FileInfo(TypedDict):
    file_path: str        # 新しいファイルパス（+++ b/... から取得）
    hunks: list[HunkInfo]


def parse_diff(diff_text: str) -> list[FileInfo]:
    """unified diff テキストをパースしてファイルごとの hunk リストを返す。

    Args:
        diff_text: git show 等が出力する unified diff 文字列

    Returns:
        FileInfo のリスト
    """
    files: list[FileInfo] = []
    current_file: FileInfo | None = None
    current_hunk: HunkInfo | None = None

    hunk_header_re = re.compile(r"^@@\s+-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s+@@")

    for line in diff_text.splitlines():
        # 新しいファイル開始（diff --git a/... b/...）
        if line.startswith("diff --git "):
            if current_hunk is not None and current_file is not None:
                current_file["hunks"].append(current_hunk)
                current_hunk = None
            if current_file is not None:
                files.append(current_file)
            current_file = FileInfo(file_path="", hunks=[])
            continue

        # ファイルパス取得（+++ b/filepath）
        if line.startswith("+++ b/") and current_file is not None:
            current_file["file_path"] = line[6:]
            continue

        # /dev/null の場合（ファイル削除）
        if line.startswith("+++ /dev/null") and current_file is not None:
            current_file["file_path"] = "/dev/null"
            continue

        # hunk ヘッダー
        if hunk_header_re.match(line) and current_file is not None:
            if current_hunk is not None:
                current_file["hunks"].append(current_hunk)
            current_hunk = HunkInfo(header=line, body_lines=[], hunk_hash="")
            continue

        # hunk 本文
        if current_hunk is not None and (
            line.startswith("+")
            or line.startswith("-")
            or line.startswith(" ")
        ):
            current_hunk["body_lines"].append(line)

    # 最後のhunk/fileを追加
    if current_hunk is not None and current_file is not None:
        current_file["hunks"].append(current_hunk)
    if current_file is not None:
        files.append(current_file)

    # hunk が空のファイル（バイナリ等）を除外
    files = [f for f in files if f["hunks"]]

    return files
