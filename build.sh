#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# 環境変数を直接エクスポート
export SECRET_KEY="${SECRET_KEY:-temporary-build-key-$(openssl rand -hex 32)}"
export DEBUG="${DEBUG:-False}"
export ALLOWED_HOSTS="${ALLOWED_HOSTS:-.onrender.com,localhost,127.0.0.1}"

echo "Starting collectstatic and migrate..."

# collectstatic と migrate を実行
python manage.py collectstatic --no-input
python manage.py migrate

echo "Build completed successfully!"
