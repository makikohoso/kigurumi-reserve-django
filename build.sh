#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# ビルド時に必要な環境変数を設定（本番環境では実際の値が環境変数から読み込まれる）
export SECRET_KEY="${SECRET_KEY:-temporary-build-key-$(openssl rand -hex 32)}"
export ALLOWED_HOSTS="${ALLOWED_HOSTS:-localhost,127.0.0.1,.onrender.com}"
export DEBUG="${DEBUG:-False}"

python manage.py collectstatic --no-input
python manage.py migrate
