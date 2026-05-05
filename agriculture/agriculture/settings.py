"""
Django settings for agriculture project — Production Ready
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================
# 🔐 SECURITY
# =============================================

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,aqriculture-ticket-system.onrender.com').split(',')

# Production security headers (only active when DEBUG=False)
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True              # HTTP → HTTPS redirect
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # For Railway/Render
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True


# =============================================
# 📦 INSTALLED APPS
# =============================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'user',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'cloudinary_storage',
    'cloudinary',
]


# =============================================
# 🔧 MIDDLEWARE
# =============================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'user.middleware.JWTAuthMiddleware',
]

ROOT_URLCONF = 'agriculture.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'user.context_processors.admin_notifications',
                'user.context_processors.staff_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'agriculture.wsgi.application'


# =============================================
# 🗄️ DATABASE
# =============================================

import dj_database_url

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Railway/Render gives a single DATABASE_URL — use it directly
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,        # ✅ Reuse DB connections for 10 mins (faster)
            ssl_require=not DEBUG,   # ✅ SSL in production
        )
    }
else:
    # Fallback: manual config for local dev
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     os.getenv('DB_NAME'),
            'USER':     os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST':     os.getenv('DB_HOST', 'localhost'),
            'PORT':     os.getenv('DB_PORT', '5432'),
            'CONN_MAX_AGE': 600,
        }
    }


# =============================================
# 🔑 PASSWORD VALIDATORS
# =============================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# =============================================
# 🔐 SESSION SETTINGS
# =============================================

SESSION_COOKIE_NAME             = 'main_session'
SESSION_COOKIE_SAMESITE         = 'Lax'
SESSION_COOKIE_HTTPONLY         = True
SESSION_COOKIE_SECURE           = not DEBUG
SESSION_COOKIE_AGE              = 86400
SESSION_SAVE_EVERY_REQUEST      = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_ENGINE                  = 'django.contrib.sessions.backends.db'


# =============================================
# 🛡️ CSRF SETTINGS
# =============================================

CSRF_COOKIE_SAMESITE  = 'Lax'
CSRF_COOKIE_HTTPONLY  = False
CSRF_COOKIE_SECURE    = not DEBUG

# ✅ Add your Railway/Render domain here after deployment
CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:8000,http://127.0.0.1:8000,https://aqriculture-ticket-system.onrender.com'
).split(',')


# =============================================
# ⚡ CACHE
# =============================================

REDIS_URL = os.getenv('REDIS_URL')

if REDIS_URL:
    # ✅ Production: Redis cache (fast, persistent across restarts)
    CACHES = {
        'default': {
            'BACKEND':  'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
else:
    # Local dev: in-memory cache (fine for development)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }


# =============================================
# 🔑 JWT SETTINGS
# =============================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':    timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME':   timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':    True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES':        ('Bearer',),
}


# =============================================
# 🌍 INTERNATIONALIZATION
# =============================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_TZ        = True


# =============================================
# 📧 EMAIL
# =============================================

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # ✅ Production: real SMTP email
    EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST          = 'smtp.gmail.com'
    EMAIL_PORT          = 587
    EMAIL_USE_TLS       = True
    EMAIL_HOST_USER     = os.getenv('EMAIL_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASSWORD')   # Use Gmail App Password
    DEFAULT_FROM_EMAIL  = os.getenv('EMAIL_USER')


# =============================================
# 📁 STATIC & MEDIA
# =============================================

STATIC_URL  = '/static/'

# ✅ Collect static from ALL apps, not just 'user'
STATICFILES_DIRS = [
    d for d in [
        BASE_DIR / 'user' / 'static',
        BASE_DIR / 'static',
    ] if d.exists()   # only include if folder exists
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

# ✅ WhiteNoise compressed static files for production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =============================================
# 📝 LOGGING
# =============================================

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)   # auto-create logs/ folder

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            # ✅ Logs saved to file in production for debugging
            'class':     'logging.handlers.RotatingFileHandler',
            'filename':  LOGS_DIR / 'django.log',
            'maxBytes':  1024 * 1024 * 5,    # 5 MB max per log file
            'backupCount': 3,                # keep last 3 log files
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers':  ['console', 'file'],
            'level':     'WARNING',
            'propagate': True,
        },
        'user': {
            'handlers':  ['console', 'file'],
            'level':     'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
    },
}


FAST2SMS_API_KEY = os.getenv('FAST2SMS_API_KEY')


import cloudinary

INSTALLED_APPS += ['cloudinary_storage', 'cloudinary']

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('dhaq2g9ht'),
    'API_KEY': os.getenv('151516687977788'),
    'API_SECRET': os.getenv('Sp2qnAMQryQmLnNs06YMQ9q6tUc'),
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'