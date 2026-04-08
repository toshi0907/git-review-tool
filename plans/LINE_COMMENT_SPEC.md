# 行単位コメント機能 仕様書

トラッキング: toshi0907/git-review-tool#9

---

## 目的

hunk 内の特定行に対してコメントを付与できる行コメント機能の仕様を明文化する。

---

## DB キー設計

### テーブル: `line_comments`

| カラム名       | 型      | 説明                                              |
|--------------|---------|--------------------------------------------------|
| session_id   | INTEGER | どのレビューセッションに属する行コメントかを示す ID     |
| hunk_hash    | TEXT    | 行コメントが属する hunk を特定するためのハッシュ値      |
| new_line_num | INTEGER | 変更後ファイル（target 側）での行番号                 |
| comment_text | TEXT    | 対象行に対するレビューコメント本文                    |
| updated_at   | TEXT    | 行コメントを最後に更新した日時（ISO 8601 形式）         |

**PRIMARY KEY: `(session_id, hunk_hash, new_line_num)`**

- `new_line_num` は target 側（変更後）の行番号を使用する。
- 削除行（target 側に行番号がない行、つまり `-` 行）はコメント対象外とする。
  追加行（`+` 行）と変更なし行（` ` 行）のみコメント可能。

---

## スコープ（実装対象）

| 操作               | 説明                                                             |
|------------------|------------------------------------------------------------------|
| **保存**          | `save_line_comment(session_id, hunk_hash, new_line_num, text)` で upsert |
| **取得（単件）**   | `get_line_comment(session_id, hunk_hash, new_line_num)` → `str`  |
| **取得（一覧）**   | `get_line_comments_for_hunk(session_id, hunk_hash)` → `dict[int, str]`（行番号→コメント） |
| **削除**          | `delete_line_comment(session_id, hunk_hash, new_line_num)` で特定行のコメントを削除 |
| **再表示**        | ページ読み込み時に保存済み行コメントを hunk に付与して表示する          |

---

## スコープ外

- **複数コメントスレッド**: 1 行に対して複数のコメントを持つスレッド機能は対象外。
  1 行につきコメント 1 件（upsert で上書き）に限定する。
- **通知機能**: コメントの通知・メール送信等は対象外。
- **コメント履歴管理**: コメントの変更履歴追跡は対象外。
- **削除行へのコメント**: `-` 行（target 側に行番号がない行）はコメント対象外。
- **行単位レビュー済みフラグ**: 行単位の `is_reviewed` フラグは対象外（hunk 単位のみ）。

---

## 制約と注意事項

1. **行番号の安定性**: `new_line_num` はコミット間で変化する可能性がある。
   コメントは `(session_id, hunk_hash, new_line_num)` の組み合わせで識別されるため、
   hunk 内容が同一（同じ `hunk_hash`）であれば、対応する `new_line_num` も同一となる。

2. **コメント削除 vs 空文字保存**: 空文字で `save_line_comment` を呼ぶと空文字が保存される。
   行コメントを完全に除去したい場合は `delete_line_comment` を使用すること。

3. **スキーマバージョン管理**: `line_comments` テーブルの追加に伴い、
   `CURRENT_SCHEMA_VERSION` を `"3"` に更新する。
   旧バージョン（`"2"`）の DB は廃棄して再作成する（マイグレーションなし方針）。

---

## API 設計（Storage クラス）

```python
def save_line_comment(
    self,
    hunk_hash: str,
    new_line_num: int,
    comment_text: str,
    session_id: int = 0,
) -> None:
    """行コメントを保存（既存は上書き）。"""

def get_line_comment(
    self,
    hunk_hash: str,
    new_line_num: int,
    session_id: int = 0,
) -> str:
    """行コメントを取得。未保存なら空文字を返す。"""

def get_line_comments_for_hunk(
    self,
    hunk_hash: str,
    session_id: int = 0,
) -> dict[int, str]:
    """hunk 内の全行コメントを {new_line_num: comment_text} で返す。"""

def delete_line_comment(
    self,
    hunk_hash: str,
    new_line_num: int,
    session_id: int = 0,
) -> None:
    """特定行のコメントを削除する。"""
```

---

## 後続ステップへの引き継ぎ

本仕様書（Step 1）の内容を確定した後、以下のステップで実装を進める。

| ステップ | 内容                                          |
|--------|----------------------------------------------|
| Step 2 | Storage クラスへの行コメント CRUD メソッド実装    |
| Step 3 | Web API エンドポイント追加（`/api/line_comment`）|
| Step 4 | テンプレート・フロントエンド UI 実装              |
| Step 5 | 削除行（`-` 行）の UI 上での無効化              |
| Step 6 | 再表示時の行コメント復元                        |
| Step 7 | E2E テスト追加                               |
| Step 8 | ドキュメント更新                              |
| Step 9 | 動作確認・レビュー                             |
