#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# ビルド時に一時的なSECRET_KEYを設定（本番環境では環境変数から読み込まれる）
export SECRET_KEY="${SECRET_KEY:-temporary-build-key-$(openssl rand -hex 32)}"

python manage.py collectstatic --no-input
python manage.py migrate
