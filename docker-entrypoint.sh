#!/bin/sh
set -e

if [ -z "$COMMIT" ]; then
    echo "エラー: COMMIT 環境変数が設定されていません。" >&2
    echo "使い方: COMMIT=<hash> docker compose up" >&2
    echo "" >&2
    echo "例:" >&2
    echo "  COMMIT=abc1234 docker compose up" >&2
    echo "  COMMIT=abc1234 BASE=def5678 docker compose up" >&2
    exit 1
fi

set -- "$COMMIT" --repo /repo --db /data/review_tool.sqlite3 --host 0.0.0.0 --port 5000

if [ -n "$BASE" ]; then
    set -- "$@" --base "$BASE"
fi

if [ -n "$ENCODING" ]; then
    set -- "$@" --encoding "$ENCODING"
fi

exec git-review-tool "$@"
