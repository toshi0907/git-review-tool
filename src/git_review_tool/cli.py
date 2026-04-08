"""CLI エントリーポイント"""
from __future__ import annotations

import argparse
import sys
import os

from .git_ops import get_diff
from .diff_parser import parse_diff
from .hunk_id import compute_hunk_hash
from .storage import Storage
from .webapp import create_app


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-review-tool",
        description="gitコミットの差分をブラウザでレビューするツール",
    )
    parser.add_argument("commit", help="レビュー対象のコミットハッシュ")
    parser.add_argument(
        "--base",
        default=None,
        metavar="COMMIT",
        help="比較元コミット（指定時は base..commit の差分を表示）",
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
    if args.base:
        print(f"差分 {args.base}..{args.commit} を取得中...")
    else:
        print(f"コミット {args.commit} の差分を取得中...")
    try:
        diff_text = get_diff(args.commit, repo_path, base=args.base)
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
    base_revision = args.base if args.base else f"{args.commit}^"
    target_revision = args.commit
    session_id = storage.get_or_create_session(
        repository_path=repo_path,
        base_revision=base_revision,
        target_revision=target_revision,
    )

    # Flask アプリ起動
    commit_label = (
        f"{args.base}..{args.commit}" if args.base else args.commit
    )
    app = create_app(
        files=files,
        storage=storage,
        commit=commit_label,
        session_id=session_id,
    )
    print(f"ブラウザで http://{args.host}:{args.port}/ を開いてください。")
    print("終了するには Ctrl+C を押してください。")
    app.run(host=args.host, port=args.port, debug=False)
