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

# 静的ファイルの収集
RUN python manage.py collectstatic --noinput

# ログディレクトリの作成
RUN mkdir -p logs

# ポート8000を公開
EXPOSE 8000

# 本番環境でのGUnicornサーバー起動
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "config.wsgi:application"]