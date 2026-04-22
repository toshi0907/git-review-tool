"""git コマンドを使って unified diff を取得する"""
from __future__ import annotations

import subprocess

from .encoding_utils import detect_and_decode


def get_diff(
    target: str,
    repo_path: str = ".",
    base: str | None = None,
    encoding: str | None = None,
) -> str:
    """unified diff を返す。

    Args:
        target: ターゲットのコミットハッシュ（または参照）
        repo_path: gitリポジトリのパス
        base: ベースのコミットハッシュ（指定時は2コミット間差分）
        encoding: 差分のエンコーディング（指定時は自動検出をスキップ）

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
            "-c",
            f"safe.directory={repo_path}",
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
            "-c",
            f"safe.directory={repo_path}",
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
            text=False,
        )
    except FileNotFoundError:
        raise ValueError("git コマンドが見つかりません。gitをインストールしてください。")

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"{cmd_name} が失敗しました（対象: {ref_label}）: {stderr}")

    if encoding:
        return result.stdout.decode(encoding)
    return detect_and_decode(result.stdout)


def resolve_merge_base(
    base_branch: str,
    repo_path: str = ".",
    head: str = "HEAD",
) -> str:
    """ベースブランチとHEADのmerge-baseを返す。"""
    cmd = [
        "git",
        "-C",
        repo_path,
        "-c",
        f"safe.directory={repo_path}",
        "merge-base",
        base_branch,
        head,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise ValueError("git コマンドが見つかりません。gitをインストールしてください。")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise ValueError(
            f"git merge-base が失敗しました（対象: {base_branch} と {head}）: {stderr}"
        )

    merge_base = result.stdout.strip()
    if not merge_base:
        raise ValueError(
            f"merge-base が見つかりませんでした（対象: {base_branch} と {head}）"
        )
    return merge_base


def find_target_commit_by_message(
    base: str,
    keyword: str,
    repo_path: str = ".",
    head: str = "HEAD",
) -> str:
    """base..head のコミットからキーワードに一致する最新コミットを返す。"""
    cmd = [
        "git",
        "-C",
        repo_path,
        "-c",
        f"safe.directory={repo_path}",
        "log",
        "--format=%H",
        "--fixed-strings",
        f"--grep={keyword}",
        f"{base}..{head}",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise ValueError("git コマンドが見つかりません。gitをインストールしてください。")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise ValueError(f"git log が失敗しました（対象: {base}..{head}）: {stderr}")

    target = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
    if not target:
        raise ValueError(
            "コミットメッセージに指定キーワードを含むコミットが見つかりませんでした。"
        )
    return target
