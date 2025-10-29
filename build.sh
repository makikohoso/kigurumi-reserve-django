#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# 現在のディレクトリを確認
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"

# 環境変数を直接エクスポート
export SECRET_KEY="${SECRET_KEY:-temporary-build-key-$(openssl rand -hex 32)}"
export DEBUG="${DEBUG:-False}"
export ALLOWED_HOSTS="${ALLOWED_HOSTS:-.onrender.com,localhost,127.0.0.1}"

# デバッグ: 環境変数の確認（SECRET_KEYは表示しない）
echo "DEBUG is set to: $DEBUG"
echo "ALLOWED_HOSTS is set to: $ALLOWED_HOSTS"

# ログディレクトリの作成（エラー回避）
mkdir -p logs

# collectstatic と migrate を実行（デフォルトのsettings.pyを使用）
python manage.py collectstatic --no-input
python manage.py migrate
