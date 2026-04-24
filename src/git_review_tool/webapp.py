"""Flask Webアプリケーション"""
from __future__ import annotations

import os.path
import re
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .storage import Storage
from .syntax import get_pygments_css, highlight_diff_lines


_DIFF_HUNK_HEADER_PATTERN = re.compile(
    # @@ -old_start[,old_count] +new_start[,new_count] @@
    # capture group 1: old_start, capture group 2: new_start
    r"^@@\s+-(\d+)(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@"
)


def _build_render_lines(hunk: dict, line_comments: dict[int, str]) -> list[dict]:
    """hunk の表示行データを構築し、行コメント表示情報を付与する。

    Args:
        hunk: header/body_lines/highlighted_lines を持つ hunk 情報
        line_comments: new line 番号をキーにした行コメント辞書

    Returns:
        行描画に必要な辞書リスト。削除行は ``new_line_num`` が None になる。
        old_line_num は削除・文脈行で進み、new_line_num は追加・文脈行で進む。
    """
    match = _DIFF_HUNK_HEADER_PATTERN.match(hunk["header"])
    if not match:
        return [
            {
                "type": line["type"],
                "prefix": line["prefix"],
                "html": line["html"],
                "new_line_num": None,
                "saved_line_comment": "",
            }
            for line in hunk["highlighted_lines"]
        ]

    old_line_num = int(match.group(1))
    new_line_num = int(match.group(2))
    render_lines: list[dict] = []
    for i, body_line in enumerate(hunk["body_lines"]):
        highlighted_line = hunk["highlighted_lines"][i]
        prefix = body_line[:1]
        current_new_line_num: int | None = None
        if prefix == "+":
            current_new_line_num = new_line_num
            new_line_num += 1
        elif prefix == "-":
            old_line_num += 1
        else:
            old_line_num += 1
            current_new_line_num = new_line_num
            new_line_num += 1

        render_lines.append(
            {
                "type": highlighted_line["type"],
                "prefix": highlighted_line["prefix"],
                "html": highlighted_line["html"],
                "new_line_num": current_new_line_num,
                "saved_line_comment": (
                    line_comments.get(current_new_line_num, "")
                    if current_new_line_num is not None
                    else ""
                ),
            }
        )
    return render_lines


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
        line_comments_map = storage.get_line_comments_batch(
            all_hashes, session_id=session_id
        )

        for f in files:
            for hunk in f["hunks"]:
                h = hunk["hunk_hash"]
                hunk["saved_comment"] = comments.get(h, "")
                hunk["is_reviewed"] = reviewed_map.get(h, False)
                hunk["render_lines"] = _build_render_lines(
                    hunk,
                    line_comments=line_comments_map.get(h, {}),
                )
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

    @app.route("/api/line-comment", methods=["POST"])
    def api_line_comment():
        data = request.get_json(force=True)
        hunk_hash = data.get("hunk_hash", "").strip()
        try:
            new_line_num = int(data.get("new_line_num", 0))
        except (TypeError, ValueError):
            new_line_num = 0
        comment_text = data.get("comment_text", "")
        if not hunk_hash:
            return jsonify({"ok": False, "error": "hunk_hash is required"}), 400
        if new_line_num <= 0:
            return jsonify({"ok": False, "error": "new_line_num is required"}), 400
        storage.save_line_comment(
            hunk_hash=hunk_hash,
            new_line_num=new_line_num,
            comment_text=comment_text,
            session_id=session_id,
        )
        return jsonify({"ok": True})

    @app.route("/api/line-comment", methods=["DELETE"])
    def api_line_comment_delete():
        data = request.get_json(force=True)
        hunk_hash = data.get("hunk_hash", "").strip()
        try:
            new_line_num = int(data.get("new_line_num", 0))
        except (TypeError, ValueError):
            new_line_num = 0
        if not hunk_hash:
            return jsonify({"ok": False, "error": "hunk_hash is required"}), 400
        if new_line_num <= 0:
            return jsonify({"ok": False, "error": "new_line_num is required"}), 400
        storage.delete_line_comment(
            hunk_hash=hunk_hash,
            new_line_num=new_line_num,
            session_id=session_id,
        )
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
