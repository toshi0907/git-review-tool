"""git コマンドを使って unified diff を取得する"""
from __future__ import annotations

import subprocess


def get_diff(target: str, repo_path: str = ".", base: str | None = None) -> str:
    """unified diff を返す。

    Args:
        target: ターゲットのコミットハッシュ（または参照）
        repo_path: gitリポジトリのパス
        base: ベースのコミットハッシュ（指定時は2コミット間差分）

    Returns:
        unified diff 文字列

    Raises:
        ValueError: コミットが無効な場合やgit実行エラーの場合
    """
    if base:
        cmd = [
            "git",
            "-C",
            repo_path,
            "diff",
            base,
            target,
            "--diff-algorithm=myers",
            "--unified=3",
        ]
        cmd_name = "git diff"
        ref_label = f"{base}..{target}"
    else:
        cmd = [
            "git",
            "-C",
            repo_path,
            "show",
            target,
            "--format=",  # コミットメッセージを除く
            "--diff-algorithm=myers",
            "--unified=3",
        ]
        cmd_name = "git show"
        ref_label = target

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
        raise ValueError(f"{cmd_name} が失敗しました（対象: {ref_label}）: {stderr}")

    return result.stdout
