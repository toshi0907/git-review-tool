"""Flask Webアプリケーション"""
from __future__ import annotations

import os.path
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .storage import Storage
from .syntax import get_pygments_css, highlight_diff_lines


def create_app(
    files: list[dict],
    storage: Storage,
    commit: str,
    session_id: int = 0,
) -> Flask:
    """Flask アプリを生成して返す。

    Args:
        files: parse_diff の返り値（FileInfo のリスト）
        storage: Storage インスタンス
        commit: レビュー対象コミットハッシュ

    Returns:
        Flask アプリインスタンス
    """
    template_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )

    # Jinja2 カスタムフィルター
    app.jinja_env.filters["basename"] = os.path.basename

    # シンタックスハイライトをアプリ起動時に一度だけ適用
    pygments_css = get_pygments_css()
    for f in files:
        for hunk in f["hunks"]:
            hunk["highlighted_lines"] = highlight_diff_lines(
                hunk["body_lines"], f["file_path"]
            )

    @app.route("/")
    def index():
        # 全 hunk_hash を収集してバッチ取得
        all_hashes = [
            hunk["hunk_hash"]
            for f in files
            for hunk in f["hunks"]
        ]
        comments = storage.get_comments_batch(all_hashes, session_id=session_id)
        reviewed_map = storage.get_reviewed_batch(all_hashes, session_id=session_id)

        for f in files:
            for hunk in f["hunks"]:
                h = hunk["hunk_hash"]
                hunk["saved_comment"] = comments.get(h, "")
                hunk["is_reviewed"] = reviewed_map.get(h, False)
        return render_template(
            "review.html",
            files=files,
            commit=commit,
            session_id=session_id,
            pygments_css=pygments_css,
        )

    @app.route("/api/comment", methods=["POST"])
    def api_comment():
        data = request.get_json(force=True)
        hunk_hash = data.get("hunk_hash", "").strip()
        comment_text = data.get("comment_text", "")
        if not hunk_hash:
            return jsonify({"ok": False, "error": "hunk_hash is required"}), 400
        storage.save_comment(hunk_hash, comment_text, session_id=session_id)
        return jsonify({"ok": True})

    @app.route("/api/comment", methods=["DELETE"])
    def api_comment_delete():
        data = request.get_json(force=True)
        hunk_hash = data.get("hunk_hash", "").strip()
        if not hunk_hash:
            return jsonify({"ok": False, "error": "hunk_hash is required"}), 400
        storage.delete_comment(hunk_hash, session_id=session_id)
        return jsonify({"ok": True})

    @app.route("/api/reviewed", methods=["POST"])
    def api_reviewed():
        data = request.get_json(force=True)
        hunk_hash = data.get("hunk_hash", "").strip()
        is_reviewed = bool(data.get("is_reviewed", False))
        if not hunk_hash:
            return jsonify({"ok": False, "error": "hunk_hash is required"}), 400
        storage.save_reviewed(hunk_hash, is_reviewed, session_id=session_id)
        return jsonify({"ok": True})

    return app
