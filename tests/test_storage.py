"""storage モジュールの統合テスト（インメモリ SQLite 使用）"""
from __future__ import annotations

import pytest
from git_review_tool.storage import Storage


@pytest.fixture
def storage(tmp_path):
    """テストごとに一時 SQLite ファイルを使う Storage インスタンスを返す"""
    return Storage(str(tmp_path / "test_review.sqlite3"))


class TestStorageComment:
    def test_get_comment_returns_empty_if_not_saved(self, storage):
        assert storage.get_comment("nonexistent") == ""

    def test_save_and_get_comment(self, storage):
        storage.save_comment("hash1", "test comment")
        assert storage.get_comment("hash1") == "test comment"

    def test_save_comment_overwrite(self, storage):
        storage.save_comment("hash1", "first")
        storage.save_comment("hash1", "second")
        assert storage.get_comment("hash1") == "second"

    def test_save_empty_comment(self, storage):
        storage.save_comment("hash1", "something")
        storage.save_comment("hash1", "")
        assert storage.get_comment("hash1") == ""

    def test_save_unicode_comment(self, storage):
        storage.save_comment("hash1", "日本語コメント")
        assert storage.get_comment("hash1") == "日本語コメント"

    def test_multiple_hashes_independent(self, storage):
        storage.save_comment("hash1", "comment1")
        storage.save_comment("hash2", "comment2")
        assert storage.get_comment("hash1") == "comment1"
        assert storage.get_comment("hash2") == "comment2"

    def test_delete_comment(self, storage):
        storage.save_comment("hash1", "delete me")
        storage.delete_comment("hash1")
        assert storage.get_comment("hash1") == ""


class TestStorageCommentBatch:
    def test_empty_hashes_returns_empty_dict(self, storage):
        assert storage.get_comments_batch([]) == {}

    def test_batch_returns_saved_comments(self, storage):
        storage.save_comment("a", "comment_a")
        storage.save_comment("b", "comment_b")
        result = storage.get_comments_batch(["a", "b"])
        assert result == {"a": "comment_a", "b": "comment_b"}

    def test_batch_omits_missing_hashes(self, storage):
        storage.save_comment("a", "comment_a")
        result = storage.get_comments_batch(["a", "missing"])
        assert "a" in result
        assert "missing" not in result

    def test_batch_all_missing(self, storage):
        result = storage.get_comments_batch(["x", "y"])
        assert result == {}


class TestStorageReviewed:
    def test_get_reviewed_returns_false_if_not_saved(self, storage):
        assert storage.get_reviewed("nonexistent") is False

    def test_save_and_get_reviewed_true(self, storage):
        storage.save_reviewed("hash1", True)
        assert storage.get_reviewed("hash1") is True

    def test_save_and_get_reviewed_false(self, storage):
        storage.save_reviewed("hash1", True)
        storage.save_reviewed("hash1", False)
        assert storage.get_reviewed("hash1") is False

    def test_reviewed_overwrite(self, storage):
        storage.save_reviewed("hash1", False)
        storage.save_reviewed("hash1", True)
        assert storage.get_reviewed("hash1") is True

    def test_multiple_hashes_independent(self, storage):
        storage.save_reviewed("hash1", True)
        storage.save_reviewed("hash2", False)
        assert storage.get_reviewed("hash1") is True
        assert storage.get_reviewed("hash2") is False


class TestStorageReviewedBatch:
    def test_empty_hashes_returns_empty_dict(self, storage):
        assert storage.get_reviewed_batch([]) == {}

    def test_batch_returns_saved_status(self, storage):
        storage.save_reviewed("a", True)
        storage.save_reviewed("b", False)
        result = storage.get_reviewed_batch(["a", "b"])
        assert result["a"] is True
        assert result["b"] is False

    def test_batch_omits_missing_hashes(self, storage):
        storage.save_reviewed("a", True)
        result = storage.get_reviewed_batch(["a", "missing"])
        assert "a" in result
        assert "missing" not in result

    def test_batch_all_missing(self, storage):
        result = storage.get_reviewed_batch(["x", "y"])
        assert result == {}


class TestStoragePersistence:
    def test_data_persists_across_instances(self, tmp_path):
        db_path = str(tmp_path / "persist.sqlite3")
        s1 = Storage(db_path)
        s1.save_comment("hash1", "persistent comment")
        s1.save_reviewed("hash1", True)

        # 新しいインスタンスで読み込み
        s2 = Storage(db_path)
        assert s2.get_comment("hash1") == "persistent comment"
        assert s2.get_reviewed("hash1") is True


class TestStorageSession:
    def test_get_or_create_session_returns_same_id(self, storage):
        s1 = storage.get_or_create_session("/repo", "a1", "b1")
        s2 = storage.get_or_create_session("/repo", "a1", "b1")
        assert s1 == s2

    def test_session_scoped_comment(self, storage):
        s1 = storage.get_or_create_session("/repo", "a1", "b1")
        s2 = storage.get_or_create_session("/repo", "a2", "b2")
        storage.save_comment("hash", "comment session1", session_id=s1)
        storage.save_comment("hash", "comment session2", session_id=s2)
        assert storage.get_comment("hash", session_id=s1) == "comment session1"
        assert storage.get_comment("hash", session_id=s2) == "comment session2"

    def test_repository_session_is_stable_for_same_repo(self, storage):
        s1 = storage.get_or_create_repository_session("/repo")
        s2 = storage.get_or_create_repository_session("/repo")
        assert s1 == s2


class TestStorageCorruptionRecovery:
    def test_corrupted_db_is_recreated(self, tmp_path):
        db_path = tmp_path / "broken.sqlite3"
        db_path.write_text("not a sqlite database", encoding="utf-8")

        storage = Storage(str(db_path))
        storage.save_comment("hash1", "ok")

        assert storage.get_comment("hash1") == "ok"
