FROM python:3.11-slim

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    gcc \
    libc-dev \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリの設定
WORKDIR /app

# 依存関係ファイルのコピーとインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# 画像ファイルを明示的にコピー（重要：Gitから取得）
COPY media/ /app/media/

# 静的ファイルの収集
RUN python manage.py collectstatic --noinput

# entrypointスクリプトをコピーして実行権限を付与
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ポート8000を公開
EXPOSE 8000

# 起動時にマイグレーションを実行してからgunicorn起動
ENTRYPOINT ["/entrypoint.sh"]