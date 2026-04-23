"""webapp モジュールのテスト（Flask テストクライアント使用）"""
from __future__ import annotations

import json
import pytest
from git_review_tool.storage import Storage
from git_review_tool.webapp import create_app


SAMPLE_FILES = [
    {
        "file_path": "foo.py",
        "hunks": [
            {
                "header": "@@ -1,3 +1,4 @@",
                "body_lines": [" line1", "-line2", "+line2 modified"],
                "hunk_hash": "abc123",
            }
        ],
    }
]


@pytest.fixture
def storage(tmp_path):
    return Storage(str(tmp_path / "test.sqlite3"))


@pytest.fixture
def client(storage):
    app = create_app(
        SAMPLE_FILES,
        storage,
        commit="deadbeef",
        session_id=0,
    )
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestIndexRoute:
    def test_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_contains_commit_hash(self, client):
        resp = client.get("/")
        assert b"deadbeef" in resp.data

    def test_contains_file_path(self, client):
        resp = client.get("/")
        assert b"foo.py" in resp.data

    def test_contains_hunk_hash(self, client):
        resp = client.get("/")
        assert b"abc123" in resp.data

    def test_contains_diff_lines(self, client):
        resp = client.get("/")
        # シンタックスハイライト後もトークン文字列自体は含まれる
        assert b"line2" in resp.data

    def test_shows_saved_comment(self, client, storage):
        storage.save_comment("abc123", "existing comment")
        resp = client.get("/")
        assert b"existing comment" in resp.data

    def test_shows_saved_line_comment(self, client, storage):
        storage.save_line_comment("abc123", 2, "line existing comment")
        resp = client.get("/")
        assert b"line existing comment" in resp.data

    def test_reviewed_hunk_is_rendered_collapsed_compact(self, client, storage):
        storage.save_reviewed("abc123", True)
        resp = client.get("/")
        assert b"is-reviewed is-collapsed" in resp.data
        assert "\u2713 \u30b3\u30f3\u30d1\u30af\u30c8\u8868\u793a".encode("utf-8") in resp.data


class TestApiComment:
    def test_save_comment_success(self, client, storage):
        resp = client.post(
            "/api/comment",
            data=json.dumps({"hunk_hash": "abc123", "comment_text": "nice code"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True
        assert storage.get_comment("abc123") == "nice code"

    def test_missing_hunk_hash_returns_400(self, client):
        resp = client.post(
            "/api/comment",
            data=json.dumps({"comment_text": "no hash"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.get_json()["ok"] is False

    def test_empty_hunk_hash_returns_400(self, client):
        resp = client.post(
            "/api/comment",
            data=json.dumps({"hunk_hash": "  ", "comment_text": "text"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_save_empty_comment(self, client, storage):
        resp = client.post(
            "/api/comment",
            data=json.dumps({"hunk_hash": "abc123", "comment_text": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert storage.get_comment("abc123") == ""

    def test_overwrite_comment(self, client, storage):
        client.post(
            "/api/comment",
            data=json.dumps({"hunk_hash": "abc123", "comment_text": "first"}),
            content_type="application/json",
        )
        client.post(
            "/api/comment",
            data=json.dumps({"hunk_hash": "abc123", "comment_text": "second"}),
            content_type="application/json",
        )
        assert storage.get_comment("abc123") == "second"

    def test_delete_comment(self, client, storage):
        storage.save_comment("abc123", "to be deleted")
        resp = client.delete(
            "/api/comment",
            data=json.dumps({"hunk_hash": "abc123"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True
        assert storage.get_comment("abc123") == ""

    def test_delete_comment_missing_hash(self, client):
        resp = client.delete(
            "/api/comment",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400


class TestApiReviewed:
    def test_mark_reviewed_true(self, client, storage):
        resp = client.post(
            "/api/reviewed",
            data=json.dumps({"hunk_hash": "abc123", "is_reviewed": True}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True
        assert storage.get_reviewed("abc123") is True

    def test_mark_reviewed_false(self, client, storage):
        storage.save_reviewed("abc123", True)
        resp = client.post(
            "/api/reviewed",
            data=json.dumps({"hunk_hash": "abc123", "is_reviewed": False}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert storage.get_reviewed("abc123") is False

    def test_missing_hunk_hash_returns_400(self, client):
        resp = client.post(
            "/api/reviewed",
            data=json.dumps({"is_reviewed": True}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.get_json()["ok"] is False

    def test_empty_hunk_hash_returns_400(self, client):
        resp = client.post(
            "/api/reviewed",
            data=json.dumps({"hunk_hash": "", "is_reviewed": True}),
            content_type="application/json",
        )
        assert resp.status_code == 400


class TestApiLineComment:
    def test_save_line_comment_success(self, client, storage):
        resp = client.post(
            "/api/line-comment",
            data=json.dumps(
                {
                    "hunk_hash": "abc123",
                    "new_line_num": 2,
                    "comment_text": "line nice code",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True
        assert storage.get_line_comment("abc123", 2) == "line nice code"

    def test_save_line_comment_missing_hunk_hash_returns_400(self, client):
        resp = client.post(
            "/api/line-comment",
            data=json.dumps({"new_line_num": 2, "comment_text": "no hash"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.get_json()["ok"] is False

    def test_save_line_comment_invalid_line_num_returns_400(self, client):
        resp = client.post(
            "/api/line-comment",
            data=json.dumps(
                {
                    "hunk_hash": "abc123",
                    "new_line_num": 0,
                    "comment_text": "invalid line",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_delete_line_comment(self, client, storage):
        storage.save_line_comment("abc123", 2, "to be deleted")
        resp = client.delete(
            "/api/line-comment",
            data=json.dumps({"hunk_hash": "abc123", "new_line_num": 2}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True
        assert storage.get_line_comment("abc123", 2) == ""

    def test_delete_line_comment_missing_line_num_returns_400(self, client):
        resp = client.delete(
            "/api/line-comment",
            data=json.dumps({"hunk_hash": "abc123"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
