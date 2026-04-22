#!/bin/sh
set -e

has_manual_commit=0
if [ -n "$GIT_REVIEW_TOOL_COMMIT" ]; then
    has_manual_commit=1
fi

has_target_keyword=0
if [ -n "$GIT_REVIEW_TOOL_AUTO_TARGET_MSG_KWD" ]; then
    has_target_keyword=1
fi

has_base_ref=0
if [ -n "$GIT_REVIEW_TOOL_AUTO_BASE_BRANCH" ] || [ -n "$GIT_REVIEW_TOOL_BASE" ]; then
    has_base_ref=1
fi

if [ "$has_manual_commit" -eq 0 ] && { [ "$has_target_keyword" -eq 0 ] || [ "$has_base_ref" -eq 0 ]; }; then
    echo "エラー: GIT_REVIEW_TOOL_COMMIT を設定するか、GIT_REVIEW_TOOL_AUTO_TARGET_MSG_KWD と GIT_REVIEW_TOOL_AUTO_BASE_BRANCH（または GIT_REVIEW_TOOL_BASE）を設定してください。" >&2
    echo "使い方: GIT_REVIEW_TOOL_COMMIT=<hash> docker compose up" >&2
    echo "        GIT_REVIEW_TOOL_COMMIT=<hash> docker-compose up  (v1をお使いの場合)" >&2
    echo "" >&2
    echo "例:" >&2
    echo "  GIT_REVIEW_TOOL_COMMIT=abc1234 docker compose up" >&2
    echo "  GIT_REVIEW_TOOL_COMMIT=abc1234 docker-compose up" >&2
    echo "  GIT_REVIEW_TOOL_AUTO_BASE_BRANCH=main GIT_REVIEW_TOOL_AUTO_TARGET_MSG_KWD='[review]' docker compose up" >&2
    echo "  GIT_REVIEW_TOOL_AUTO_BASE_BRANCH=main GIT_REVIEW_TOOL_AUTO_TARGET_MSG_KWD='[review]' docker-compose up" >&2
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

if [ -n "$GIT_REVIEW_TOOL_AUTO_BASE_BRANCH" ]; then
    set -- "$@" --base-branch "$GIT_REVIEW_TOOL_AUTO_BASE_BRANCH"
fi

if [ -n "$GIT_REVIEW_TOOL_AUTO_TARGET_MSG_KWD" ]; then
    set -- "$@" --target-message-keyword "$GIT_REVIEW_TOOL_AUTO_TARGET_MSG_KWD"
fi

if [ -n "$GIT_REVIEW_TOOL_ENCODING" ]; then
    set -- "$@" --encoding "$GIT_REVIEW_TOOL_ENCODING"
fi

exec git-review-tool "$@"
