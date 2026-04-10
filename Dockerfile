FROM python:3.11-slim

# git をインストール
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# パッケージをインストール
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir -e .

# エントリーポイントスクリプトをコピー
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["docker-entrypoint.sh"]
