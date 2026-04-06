"""git コマンドを使って unified diff を取得する"""
from __future__ import annotations

import subprocess
import sys


def get_diff(commit: str, repo_path: str = ".") -> str:
    """指定コミットと親の unified diff を返す。

    Args:
        commit: コミットハッシュ（または参照）
        repo_path: gitリポジトリのパス

    Returns:
        unified diff 文字列

    Raises:
        ValueError: コミットが無効な場合やgit実行エラーの場合
    """
    cmd = [
        "git",
        "-C", repo_path,
        "show",
        commit,
        "--format=",        # コミットメッセージを除く
        "--diff-algorithm=myers",
        "--unified=3",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        raise ValueError("git コマンドが見つかりません。gitをインストールしてください。")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise ValueError(
            f"git show が失敗しました（コミット: {commit}）: {stderr}"
        )

    return result.stdout
