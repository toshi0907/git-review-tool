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
    """ベースブランチとHEADの共通祖先コミット（merge-base）を返す。

    Args:
        base_branch: merge-base計算の基準にするブランチ名（例: main, origin/dev）
        repo_path: 対象gitリポジトリのパス
        head: 比較先の参照（通常はHEAD）

    Returns:
        base_branch と head の merge-base コミットハッシュ
    """
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
    """base..head のコミットメッセージからキーワード一致の最新コミットを返す。

    Args:
        base: 検索範囲の開始コミット（除外）
        keyword: コミットメッセージに含まれるべき文字列（固定文字列検索）
        repo_path: 対象gitリポジトリのパス
        head: 検索範囲の終了参照（通常はHEAD、含む）

    Returns:
        git log の出力順（新しい順）で最初に一致したコミットハッシュ

    Example:
        `git log --format=%H --fixed-strings --grep=[review] <base>..HEAD`
        の出力が以下の場合、戻り値は先頭行のコミットハッシュ。
        9fceb02f4f66f6f3f19d7d3e2b2f4f0fdc4a4d12
        3d2e1f90b9b4ac53f01d4ccf6d41f8b6abfe1023
    """
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

    target = ""
    for line in result.stdout.splitlines():
        candidate = line.strip()
        if candidate:
            target = candidate
            break
    if not target:
        raise ValueError(
            f"コミットメッセージに '{keyword}' を含むコミットが見つかりませんでした"
            f"（範囲: {base}..{head}）。"
        )
    return target
