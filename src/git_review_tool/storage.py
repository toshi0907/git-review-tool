"""SQLite を使ったコメント・レビュー状態の永続化"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


class Storage:
    """hunk_comments と hunk_status テーブルを管理するストレージクラス"""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hunk_comments (
                    hunk_hash  TEXT PRIMARY KEY,
                    comment_text TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hunk_status (
                    hunk_hash   TEXT PRIMARY KEY,
                    is_reviewed INTEGER NOT NULL DEFAULT 0,
                    reviewed_at TEXT
                )
            """)
            conn.commit()

    def save_comment(self, hunk_hash: str, comment_text: str) -> None:
        """コメントを保存（既存は上書き）"""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO hunk_comments (hunk_hash, comment_text, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(hunk_hash) DO UPDATE SET
                    comment_text = excluded.comment_text,
                    updated_at = excluded.updated_at
                """,
                (hunk_hash, comment_text, now),
            )
            conn.commit()

    def get_comment(self, hunk_hash: str) -> str:
        """コメントを取得。未保存なら空文字を返す"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT comment_text FROM hunk_comments WHERE hunk_hash = ?",
                (hunk_hash,),
            ).fetchone()
        return row["comment_text"] if row else ""

    def save_reviewed(self, hunk_hash: str, is_reviewed: bool) -> None:
        """レビュー済み状態を保存"""
        now = datetime.now(timezone.utc).isoformat() if is_reviewed else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO hunk_status (hunk_hash, is_reviewed, reviewed_at)
                VALUES (?, ?, ?)
                ON CONFLICT(hunk_hash) DO UPDATE SET
                    is_reviewed = excluded.is_reviewed,
                    reviewed_at = excluded.reviewed_at
                """,
                (hunk_hash, int(is_reviewed), now),
            )
            conn.commit()

    def get_reviewed(self, hunk_hash: str) -> bool:
        """レビュー済み状態を取得。未保存なら False を返す"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT is_reviewed FROM hunk_status WHERE hunk_hash = ?",
                (hunk_hash,),
            ).fetchone()
        return bool(row["is_reviewed"]) if row else False
