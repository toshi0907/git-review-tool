"""SQLite を使ったコメント・レビュー状態の永続化"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

CURRENT_SCHEMA_VERSION = "2"
REPOSITORY_SESSION_SENTINEL_BASE = "__repository_review_base__"
REPOSITORY_SESSION_SENTINEL_TARGET = "__repository_review_target__"


class Storage:
    """レビュー情報を管理するストレージクラス。"""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _reset_db_file(self) -> None:
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS review_meta (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS review_sessions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_path TEXT NOT NULL,
                base_revision   TEXT NOT NULL,
                target_revision TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                UNIQUE(repository_path, base_revision, target_revision)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hunk_comments (
                session_id   INTEGER NOT NULL DEFAULT 0,
                hunk_hash    TEXT NOT NULL,
                comment_text TEXT NOT NULL DEFAULT '',
                updated_at   TEXT NOT NULL,
                PRIMARY KEY (session_id, hunk_hash)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hunk_status (
                session_id   INTEGER NOT NULL DEFAULT 0,
                hunk_hash    TEXT NOT NULL,
                is_reviewed  INTEGER NOT NULL DEFAULT 0,
                reviewed_at  TEXT,
                PRIMARY KEY (session_id, hunk_hash)
            )
        """)
        conn.execute(
            """
            INSERT INTO review_meta (key, value)
            VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (CURRENT_SCHEMA_VERSION,),
        )

    def _init_db(self) -> None:
        try:
            with self._connect() as conn:
                tables = {
                    row["name"]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                # マイグレーションは実施しない方針。
                # 既存の旧スキーマDBは破棄して最新スキーマで再作成する。
                if tables and "review_meta" not in tables:
                    raise ValueError("legacy schema detected")

                self._create_schema(conn)
                version_row = conn.execute(
                    "SELECT value FROM review_meta WHERE key='schema_version'"
                ).fetchone()
                if not version_row or version_row["value"] != CURRENT_SCHEMA_VERSION:
                    raise ValueError("unsupported schema version")
                conn.commit()
        except (sqlite3.DatabaseError, ValueError):
            self._reset_db_file()
            with self._connect() as conn:
                self._create_schema(conn)
                conn.commit()

    def get_or_create_session(
        self,
        repository_path: str,
        base_revision: str,
        target_revision: str,
    ) -> int:
        """レビューセッションを取得または作成して ID を返す。"""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM review_sessions
                WHERE repository_path = ? AND base_revision = ? AND target_revision = ?
                """,
                (repository_path, base_revision, target_revision),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE review_sessions SET updated_at = ? WHERE id = ?",
                    (now, row["id"]),
                )
                conn.commit()
                return int(row["id"])

            cur = conn.execute(
                """
                INSERT INTO review_sessions (
                    repository_path, base_revision, target_revision, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (repository_path, base_revision, target_revision, now, now),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_or_create_repository_session(self, repository_path: str) -> int:
        """リポジトリ単位で共通利用するレビューセッションを取得または作成する。"""
        return self.get_or_create_session(
            repository_path=repository_path,
            base_revision=REPOSITORY_SESSION_SENTINEL_BASE,
            target_revision=REPOSITORY_SESSION_SENTINEL_TARGET,
        )

    def save_comment(
        self,
        hunk_hash: str,
        comment_text: str,
        session_id: int = 0,
    ) -> None:
        """コメントを保存（既存は上書き）"""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO hunk_comments (session_id, hunk_hash, comment_text, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id, hunk_hash) DO UPDATE SET
                    comment_text = excluded.comment_text,
                    updated_at = excluded.updated_at
                """,
                (session_id, hunk_hash, comment_text, now),
            )
            conn.commit()

    def get_comment(self, hunk_hash: str, session_id: int = 0) -> str:
        """コメントを取得。未保存なら空文字を返す"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT comment_text FROM hunk_comments WHERE session_id = ? AND hunk_hash = ?",
                (session_id, hunk_hash),
            ).fetchone()
        return row["comment_text"] if row else ""

    def delete_comment(self, hunk_hash: str, session_id: int = 0) -> None:
        """コメントを削除する。"""
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM hunk_comments WHERE session_id = ? AND hunk_hash = ?",
                (session_id, hunk_hash),
            )
            conn.commit()

    def get_comments_batch(
        self,
        hunk_hashes: list[str],
        session_id: int = 0,
    ) -> dict[str, str]:
        """複数の hunk_hash のコメントを一括取得する"""
        if not hunk_hashes:
            return {}
        placeholders = ",".join("?" * len(hunk_hashes))
        params: list[object] = [session_id]
        params.extend(hunk_hashes)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT hunk_hash, comment_text FROM hunk_comments WHERE session_id = ? AND hunk_hash IN ({placeholders})",
                params,
            ).fetchall()
        return {row["hunk_hash"]: row["comment_text"] for row in rows}

    def save_reviewed(
        self,
        hunk_hash: str,
        is_reviewed: bool,
        session_id: int = 0,
    ) -> None:
        """レビュー済み状態を保存"""
        now = datetime.now(timezone.utc).isoformat() if is_reviewed else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO hunk_status (session_id, hunk_hash, is_reviewed, reviewed_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id, hunk_hash) DO UPDATE SET
                    is_reviewed = excluded.is_reviewed,
                    reviewed_at = excluded.reviewed_at
                """,
                (session_id, hunk_hash, int(is_reviewed), now),
            )
            conn.commit()

    def get_reviewed(self, hunk_hash: str, session_id: int = 0) -> bool:
        """レビュー済み状態を取得。未保存なら False を返す"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT is_reviewed FROM hunk_status WHERE session_id = ? AND hunk_hash = ?",
                (session_id, hunk_hash),
            ).fetchone()
        return bool(row["is_reviewed"]) if row else False

    def get_reviewed_batch(
        self,
        hunk_hashes: list[str],
        session_id: int = 0,
    ) -> dict[str, bool]:
        """複数の hunk_hash のレビュー済み状態を一括取得する"""
        if not hunk_hashes:
            return {}
        placeholders = ",".join("?" * len(hunk_hashes))
        params: list[object] = [session_id]
        params.extend(hunk_hashes)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT hunk_hash, is_reviewed FROM hunk_status WHERE session_id = ? AND hunk_hash IN ({placeholders})",
                params,
            ).fetchall()
        return {row["hunk_hash"]: bool(row["is_reviewed"]) for row in rows}
