"""Flask Webアプリケーション"""
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .storage import Storage


def create_app(
    files: list[dict],
    storage: Storage,
    commit: str,
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

    @app.route("/")
    def index():
        # 全 hunk_hash を収集してバッチ取得
        all_hashes = [
            hunk["hunk_hash"]
            for f in files
            for hunk in f["hunks"]
        ]
        comments = storage.get_comments_batch(all_hashes)
        reviewed_map = storage.get_reviewed_batch(all_hashes)

        for f in files:
            for hunk in f["hunks"]:
                h = hunk["hunk_hash"]
                hunk["saved_comment"] = comments.get(h, "")
                hunk["is_reviewed"] = reviewed_map.get(h, False)
        return render_template("review.html", files=files, commit=commit)

    @app.route("/api/comment", methods=["POST"])
    def api_comment():
        data = request.get_json(force=True)
        hunk_hash = data.get("hunk_hash", "").strip()
        comment_text = data.get("comment_text", "")
        if not hunk_hash:
            return jsonify({"ok": False, "error": "hunk_hash is required"}), 400
        storage.save_comment(hunk_hash, comment_text)
        return jsonify({"ok": True})

    @app.route("/api/reviewed", methods=["POST"])
    def api_reviewed():
        data = request.get_json(force=True)
        hunk_hash = data.get("hunk_hash", "").strip()
        is_reviewed = bool(data.get("is_reviewed", False))
        if not hunk_hash:
            return jsonify({"ok": False, "error": "hunk_hash is required"}), 400
        storage.save_reviewed(hunk_hash, is_reviewed)
        return jsonify({"ok": True})

    return app
