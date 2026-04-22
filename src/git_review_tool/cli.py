"""CLI エントリーポイント"""
from __future__ import annotations

import argparse
import sys
import os

from .git_ops import get_diff, resolve_merge_base, find_target_commit_by_message
from .diff_parser import parse_diff
from .hunk_id import compute_hunk_hash
from .storage import Storage
from .webapp import create_app


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-review-tool",
        description="gitコミットの差分をブラウザでレビューするツール",
    )
    parser.add_argument(
        "commit",
        nargs="?",
        help="レビュー対象のコミットハッシュ（省略時は --target-message-keyword で自動検出）",
    )
    parser.add_argument(
        "--base",
        default=None,
        metavar="COMMIT",
        help="比較元コミット（指定時は base..commit の差分を表示）",
    )
    parser.add_argument(
        "--base-branch",
        default=None,
        metavar="BRANCH",
        help=(
            "比較元ブランチ名。--base 未指定時、"
            "このブランチとHEADのmerge-baseをbaseとして使用"
        ),
    )
    parser.add_argument(
        "--target-message-keyword",
        default=None,
        metavar="KEYWORD",
        help=(
            "レビュー対象コミットの自動検出キーワード。"
            "base..HEAD のコミットメッセージに一致する最新コミットを使用"
        ),
    )
    parser.add_argument(
        "--repo",
        default=".",
        metavar="PATH",
        help="gitリポジトリのパス（デフォルト: カレントディレクトリ）",
    )
    parser.add_argument(
        "--db",
        default=None,
        metavar="PATH",
        help="SQLiteデータベースのパス（デフォルト: <repo>/.git/review_tool.sqlite3）",
    )
    parser.add_argument(
        "--encoding",
        default=None,
        metavar="ENCODING",
        help="差分のエンコーディングを明示的に指定（例: euc-jp, shift_jis）。省略時は自動検出",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Flaskサーバのホスト（デフォルト: 127.0.0.1）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Flaskサーバのポート（デフォルト: 5000）",
    )

    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo)
    base = args.base
    base_branch = args.base_branch or os.getenv("GIT_REVIEW_TOOL_BASE_BRANCH")
    target_keyword = args.target_message_keyword or os.getenv(
        "GIT_REVIEW_TOOL_TARGET_MESSAGE_KEYWORD"
    )

    if not base and base_branch:
        try:
            base = resolve_merge_base(base_branch, repo_path=repo_path)
        except ValueError as exc:
            print(f"エラー: {exc}", file=sys.stderr)
            sys.exit(1)

    commit = args.commit
    if not commit and target_keyword:
        if not base:
            parser.error(
                "ターゲット自動検出には --base または --base-branch "
                "（または GIT_REVIEW_TOOL_BASE_BRANCH）が必要です。"
            )
        try:
            commit = find_target_commit_by_message(
                base=base,
                keyword=target_keyword,
                repo_path=repo_path,
            )
        except ValueError as exc:
            print(f"エラー: {exc}", file=sys.stderr)
            sys.exit(1)

    if not commit:
        parser.error(
            "commit を指定してください。自動検出する場合は "
            "--target-message-keyword を指定してください。"
        )

    # DB パスの決定
    if args.db:
        db_path = args.db
    else:
        git_dir = os.path.join(repo_path, ".git")
        if not os.path.isdir(git_dir):
            print(
                f"エラー: '{repo_path}' はgitリポジトリではありません。",
                file=sys.stderr,
            )
            sys.exit(1)
        db_path = os.path.join(git_dir, "review_tool.sqlite3")

    # diff 取得
    if base:
        print(f"差分 {base}..{commit} を取得中...")
    else:
        print(f"コミット {commit} の差分を取得中...")
    try:
        diff_text = get_diff(commit, repo_path, base=base, encoding=args.encoding)
    except ValueError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        sys.exit(1)

    if not diff_text.strip():
        print("差分が見つかりませんでした。", file=sys.stderr)
        sys.exit(0)

    # diff パース & hunk hash 付与
    files = parse_diff(diff_text)
    for f in files:
        for hunk in f["hunks"]:
            hunk["hunk_hash"] = compute_hunk_hash(f["file_path"], hunk["body_lines"])

    # ストレージ初期化
    storage = Storage(db_path)
    session_id = storage.get_or_create_repository_session(repository_path=repo_path)

    # Flask アプリ起動
    commit_label = f"{base}..{commit}" if base else commit
    app = create_app(
        files=files,
        storage=storage,
        commit=commit_label,
        session_id=session_id,
    )
    print(f"ブラウザで http://{args.host}:{args.port}/ を開いてください。")
    print("終了するには Ctrl+C を押してください。")
    app.run(host=args.host, port=args.port, debug=False)
