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

# BASEブランチとキーワードからレビュー対象を自動検出
git-review-tool --base-branch main --target-message-keyword "[review]"

# 2コミット間差分をレビュー
git-review-tool <target-commit> --base <base-commit>

# リポジトリパスを指定
git-review-tool <commit-hash> --repo /path/to/repo

# DBパス・ホスト・ポートを指定
git-review-tool <commit-hash> --repo /path/to/repo --db /tmp/review.sqlite3 --host 0.0.0.0 --port 8080

# EUC-JPエンコードのソースコードを含むリポジトリをレビュー（自動検出）
git-review-tool <commit-hash>

# エンコーディングを明示的に指定
git-review-tool <commit-hash> --encoding euc-jp
```

起動後、ブラウザで `http://127.0.0.1:5000/` を開いてください。

## オプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--base COMMIT` | なし | 指定時は `base..commit` の2コミット間差分を表示 |
| `--base-branch BRANCH` | なし | `--base` 未指定時、`BRANCH` と `HEAD` の merge-base を自動で比較元に設定 |
| `--target-message-keyword KEYWORD` | なし | `base..HEAD` のコミットメッセージに `KEYWORD` を含む最新コミットをレビュー対象として自動検出 |
| `--repo PATH` | `.`（カレントディレクトリ） | gitリポジトリのパス |
| `--db PATH` | `.git/review_tool.sqlite3` | SQLiteデータベースのパス |
| `--encoding ENCODING` | なし（自動検出） | 差分のエンコーディングを明示指定（例: `euc-jp`, `shift_jis`, `utf-8`）。省略時はUTF-8→EUC-JP→CP932の順で自動検出 |
| `--host HOST` | `127.0.0.1` | Flaskサーバのホスト |
| `--port PORT` | `5000` | Flaskサーバのポート |

## 機能

- 単一コミット差分（`git show`）と2コミット間差分（`git diff`）を表示
- コミットの unified diff を hunk 単位に分解して表示
- **非UTF-8エンコーディング対応**: UTF-8 / EUC-JP / CP932（Shift_JIS互換）を自動検出。`--encoding` オプションで明示指定も可能
- hunk ごとにコメントを入力・保存
- hunk コメントの削除
- hunk コメントのリセット（未保存変更を破棄）
- hunk ごとに「レビュー済み」チェックボックスで状態管理
- コメント・レビュー状態は SQLite に永続化（サーバ再起動後も復元）
- コメント・レビュー状態はリポジトリ単位で永続化（コミットハッシュ変更後も同一hunkなら復元）
- hunk hash（SHA256）による決定論的な hunk 識別
- DB破損時は自動でDBを再生成して復旧

## Docker Compose で使う

### 前提

- Docker / Docker Compose がインストールされていること
  - Docker Compose v2（`docker compose`）または v1（`docker-compose`）のどちらでも使用できます

### 手順

1. `.env.example` をコピーして `.env` を作成し、`GIT_REVIEW_TOOL_COMMIT`（手動指定）または `GIT_REVIEW_TOOL_BASE_BRANCH` + `GIT_REVIEW_TOOL_TARGET_MESSAGE_KEYWORD`（自動検出）を設定します。

    ```bash
    cp .env.example .env
    # .env を編集して GIT_REVIEW_TOOL_COMMIT=<hash> を設定
    ```

2. レビュー対象リポジトリのパスを指定してコンテナを起動します。

    ```bash
    # カレントディレクトリのリポジトリをレビュー（.env に GIT_REVIEW_TOOL_COMMIT が設定済みの場合）
    docker compose up          # Docker Compose v2
    docker-compose up          # Docker Compose v1

    # コマンドラインで環境変数を渡す場合（.env より優先されます）
    GIT_REVIEW_TOOL_COMMIT=abc1234 docker compose up
    GIT_REVIEW_TOOL_COMMIT=abc1234 docker-compose up   # v1

    # 別リポジトリを指定する場合
    GIT_REVIEW_TOOL_COMMIT=abc1234 GIT_REVIEW_TOOL_REPO_PATH=/path/to/repo docker compose up
    GIT_REVIEW_TOOL_COMMIT=abc1234 GIT_REVIEW_TOOL_REPO_PATH=/path/to/repo docker-compose up   # v1

    # 2コミット間差分をレビューする場合
    GIT_REVIEW_TOOL_COMMIT=abc1234 GIT_REVIEW_TOOL_BASE=def5678 docker compose up
    GIT_REVIEW_TOOL_COMMIT=abc1234 GIT_REVIEW_TOOL_BASE=def5678 docker-compose up   # v1

    # BASEブランチとキーワードでレビュー対象コミットを自動検出する場合
    GIT_REVIEW_TOOL_BASE_BRANCH=main GIT_REVIEW_TOOL_TARGET_MESSAGE_KEYWORD='[review]' docker compose up
    GIT_REVIEW_TOOL_BASE_BRANCH=main GIT_REVIEW_TOOL_TARGET_MESSAGE_KEYWORD='[review]' docker-compose up   # v1
    ```

3. ブラウザで `http://localhost:5000/` を開いてください。

4. 終了するには `Ctrl+C` を押し、コンテナを削除します。

    ```bash
    docker compose down          # Docker Compose v2
    docker-compose down          # Docker Compose v1
    ```

### 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `GIT_REVIEW_TOOL_COMMIT` | なし | レビュー対象のコミットハッシュ（手動指定時） |
| `GIT_REVIEW_TOOL_BASE` | なし | 比較元コミット（指定時は `BASE..COMMIT` の差分） |
| `GIT_REVIEW_TOOL_BASE_BRANCH` | なし | `BASE` 未指定時、`HEAD` との merge-base 算出に使うブランチ名（例: `main`, `origin/dev`） |
| `GIT_REVIEW_TOOL_TARGET_MESSAGE_KEYWORD` | なし | `BASE..HEAD` のコミットメッセージにこの文字列を含む最新コミットをレビュー対象として自動検出 |
| `GIT_REVIEW_TOOL_REPO_PATH` | `.`（カレントディレクトリ） | レビュー対象gitリポジトリのパス |
| `GIT_REVIEW_TOOL_PORT` | `5000` | ホスト側の公開ポート（コンテナ内部は常にポート 5000） |
| `GIT_REVIEW_TOOL_ENCODING` | なし（自動検出） | 差分のエンコーディング（例: `euc-jp`） |

> **注意**: コンテナ内の SQLite データベースは `review-data` という名前付きボリュームに保存されます。  
> `docker compose down -v`（v2）または `docker-compose down -v`（v1）を実行するとボリューム（レビューデータ）も削除されます。  
> `GIT_REVIEW_TOOL_REPO_PATH` で指定したリポジトリは読み取り専用でマウントされます（`git show` / `git diff` はリポジトリへの書き込みを行わないため問題ありません）。

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

- 症状: 差分が文字化けする
    - 対応: `--encoding euc-jp` や `--encoding shift_jis` のようにエンコーディングを明示的に指定してください。

- 症状: 差分が表示されない
    - 対応: 指定コミットに差分があるか確認してください。`--base` 指定時は `base` と `commit` の順序も確認してください。

- 症状: コメントや状態が消えた
    - 対応: 旧/破損DB検出時は再生成される仕様です。必要であれば `.git/review_tool.sqlite3` をバックアップして運用してください。

## ファイル構成

```
src/git_review_tool/
├── cli.py              # CLIエントリーポイント
├── git_ops.py          # git コマンド実行
├── encoding_utils.py   # エンコーディング自動検出・デコード
├── diff_parser.py      # unified diff パーサー
├── hunk_id.py          # hunk hash 生成
├── storage.py          # SQLiteストレージ
├── webapp.py           # Flask Webアプリ
├── templates/
│   └── review.html     # レビューUI
└── static/
    └── app.js          # フロントエンドJS
```
