#!/bin/sh
set -e

if [ -z "$GIT_REVIEW_TOOL_COMMIT" ] && [ -z "$GIT_REVIEW_TOOL_TARGET_MESSAGE_KEYWORD" ]; then
    echo "エラー: GIT_REVIEW_TOOL_COMMIT 環境変数が設定されていません。" >&2
    echo "使い方: GIT_REVIEW_TOOL_COMMIT=<hash> docker compose up" >&2
    echo "        GIT_REVIEW_TOOL_COMMIT=<hash> docker-compose up  (v1をお使いの場合)" >&2
    echo "" >&2
    echo "例:" >&2
    echo "  GIT_REVIEW_TOOL_COMMIT=abc1234 docker compose up" >&2
    echo "  GIT_REVIEW_TOOL_COMMIT=abc1234 docker-compose up" >&2
    echo "  GIT_REVIEW_TOOL_BASE_BRANCH=main GIT_REVIEW_TOOL_TARGET_MESSAGE_KEYWORD='[review]' docker compose up" >&2
    echo "  GIT_REVIEW_TOOL_BASE_BRANCH=main GIT_REVIEW_TOOL_TARGET_MESSAGE_KEYWORD='[review]' docker-compose up" >&2
    echo "  GIT_REVIEW_TOOL_COMMIT=abc1234 GIT_REVIEW_TOOL_BASE=def5678 docker compose up" >&2
    echo "  GIT_REVIEW_TOOL_COMMIT=abc1234 GIT_REVIEW_TOOL_BASE=def5678 docker-compose up" >&2
    exit 1
fi

set -- --repo /repo --db /data/review_tool.sqlite3 --host 0.0.0.0 --port 5000

if [ -n "$GIT_REVIEW_TOOL_COMMIT" ]; then
    set -- "$GIT_REVIEW_TOOL_COMMIT" "$@"
fi

if [ -n "$GIT_REVIEW_TOOL_BASE" ]; then
    set -- "$@" --base "$GIT_REVIEW_TOOL_BASE"
fi

if [ -n "$GIT_REVIEW_TOOL_BASE_BRANCH" ]; then
    set -- "$@" --base-branch "$GIT_REVIEW_TOOL_BASE_BRANCH"
fi

if [ -n "$GIT_REVIEW_TOOL_TARGET_MESSAGE_KEYWORD" ]; then
    set -- "$@" --target-message-keyword "$GIT_REVIEW_TOOL_TARGET_MESSAGE_KEYWORD"
fi

if [ -n "$GIT_REVIEW_TOOL_ENCODING" ]; then
    set -- "$@" --encoding "$GIT_REVIEW_TOOL_ENCODING"
fi

exec git-review-tool "$@"
