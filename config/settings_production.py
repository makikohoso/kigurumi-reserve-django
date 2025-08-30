"""
本番環境用Django設定
"""
from .settings import *
from decouple import config

# セキュリティ設定
DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

# HTTPS設定
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1年
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# クッキーセキュリティ
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'

# データベース（PostgreSQL推奨）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# 静的ファイル（CDN/S3推奨）
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# メディアファイル（S3等のオブジェクトストレージ推奨）
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='ap-northeast-1')

# ログ設定（本番用）
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/django/audit.log',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'formatter': 'json',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/django/security.log',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'formatter': 'json',
        },
        'syslog': {
            'level': 'ERROR',
            'class': 'logging.handlers.SysLogHandler',
            'address': '/dev/log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'audit': {
            'handlers': ['audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'security': {
            'handlers': ['security_file', 'syslog'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django': {
            'handlers': ['syslog'],
            'level': 'ERROR',
        },
    },
}

# パフォーマンス最適化
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'

# キャッシュ設定（Redis推奨）
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'kigurumi_reserve',
        'TIMEOUT': 300,
    }
}

# セキュリティヘッダー追加
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
SECURE_PERMISSIONS_POLICY = {
    "geolocation": [],
    "microphone": [],
    "camera": [],
}

# レート制限強化
RESERVATION_SETTINGS.update({
    'ENABLE_RATE_LIMITING': True,
    'RATE_LIMIT_PER_HOUR': 5,  # 本番では制限を厳しく
    'MAX_RESERVATIONS_PER_USER_PER_DAY': 3,  # 本番では制限を厳しく
})

# エラー監視（Sentry等）
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment=config('ENVIRONMENT', default='production'),
    )