#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# ビルド時に一時的な.envファイルを作成
cat > .env << EOF
SECRET_KEY=${SECRET_KEY:-temporary-build-key-$(openssl rand -hex 32)}
DEBUG=${DEBUG:-False}
ALLOWED_HOSTS=${ALLOWED_HOSTS:-.onrender.com,localhost,127.0.0.1}
DATABASE_URL=${DATABASE_URL:-}
EOF

python manage.py collectstatic --no-input
python manage.py migrate
