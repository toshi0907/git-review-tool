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

# リポジトリパスを指定
git-review-tool <commit-hash> --repo /path/to/repo

# DBパス・ホスト・ポートを指定
git-review-tool <commit-hash> --repo /path/to/repo --db /tmp/review.sqlite3 --host 0.0.0.0 --port 8080
```

起動後、ブラウザで `http://127.0.0.1:5000/` を開いてください。

## オプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--repo PATH` | `.`（カレントディレクトリ） | gitリポジトリのパス |
| `--db PATH` | `.git/review_tool.sqlite3` | SQLiteデータベースのパス |
| `--host HOST` | `127.0.0.1` | Flaskサーバのホスト |
| `--port PORT` | `5000` | Flaskサーバのポート |

## 機能

- コミットの unified diff を hunk 単位に分解して表示
- hunk ごとにコメントを入力・保存
- hunk ごとに「レビュー済み」チェックボックスで状態管理
- コメント・レビュー状態は SQLite に永続化（サーバ再起動後も復元）
- hunk hash（SHA256）による決定論的な hunk 識別

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
