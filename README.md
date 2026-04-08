# git-review-tool

gitコミットの差分をブラウザでセルフレビューするローカルツールです。  
hunk単位のコメント保存・レビュー完了管理ができます。

## 前提

- Python 3.8 以上
- `git` コマンドが利用可能であること
- レビュー対象ディレクトリが git リポジトリであること

## インストール

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

> Flask が依存ライブラリとして自動インストールされます。  
> 仮想環境を使わずにシステムのPythonに直接インストールしたい場合は `pip install -e . --break-system-packages` を使用してください（非推奨）。

## 使い方

```bash
# カレントディレクトリのリポジトリで指定コミットをレビュー
git-review-tool <commit-hash>

# 2コミット間差分をレビュー
git-review-tool <target-commit> --base <base-commit>

# リポジトリパスを指定
git-review-tool <commit-hash> --repo /path/to/repo

# DBパス・ホスト・ポートを指定
git-review-tool <commit-hash> --repo /path/to/repo --db /tmp/review.sqlite3 --host 0.0.0.0 --port 8080
```

起動後、ブラウザで `http://127.0.0.1:5000/` を開いてください。

## オプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--base COMMIT` | なし | 指定時は `base..commit` の2コミット間差分を表示 |
| `--repo PATH` | `.`（カレントディレクトリ） | gitリポジトリのパス |
| `--db PATH` | `.git/review_tool.sqlite3` | SQLiteデータベースのパス |
| `--host HOST` | `127.0.0.1` | Flaskサーバのホスト |
| `--port PORT` | `5000` | Flaskサーバのポート |

## 機能

- 単一コミット差分（`git show`）と2コミット間差分（`git diff`）を表示
- コミットの unified diff を hunk 単位に分解して表示
- hunk ごとにコメントを入力・保存
- hunk コメントの削除
- hunk コメントのリセット（未保存変更を破棄）
- hunk ごとに「レビュー済み」チェックボックスで状態管理
- コメント・レビュー状態は SQLite に永続化（サーバ再起動後も復元）
- レビューセッション（repository/base/target）単位で状態を分離
- hunk hash（SHA256）による決定論的な hunk 識別
- DB破損時は自動でDBを再生成して復旧

## テスト

```bash
# 開発用依存（pytest）をインストール
pip install -e ".[dev]"

# フォーマット
python -m black src tests

# テスト実行
python -m pytest
```

## ストレージ方針

- マイグレーションは実施しません。
- 常に最新バージョンのスキーマを使用します。
- 旧バージョンまたは破損したDBを検出した場合は、既存データを廃棄して最新スキーマで再生成します。

## トラブルシューティング

- 症状: `git ... が失敗しました` が表示される
    - 対応: コミット参照が正しいか、対象がgitリポジトリかを確認してください。

- 症状: 差分が表示されない
    - 対応: 指定コミットに差分があるか確認してください。`--base` 指定時は `base` と `commit` の順序も確認してください。

- 症状: コメントや状態が消えた
    - 対応: 旧/破損DB検出時は再生成される仕様です。必要であれば `.git/review_tool.sqlite3` をバックアップして運用してください。

## ファイル構成

```
src/git_review_tool/
├── cli.py          # CLIエントリーポイント
├── git_ops.py      # git コマンド実行
├── diff_parser.py  # unified diff パーサー
├── hunk_id.py      # hunk hash 生成
├── storage.py      # SQLiteストレージ
├── webapp.py       # Flask Webアプリ
├── templates/
│   └── review.html # レビューUI
└── static/
    └── app.js      # フロントエンドJS
```
