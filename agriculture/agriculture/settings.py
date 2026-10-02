"""
Django settings for agriculture project — Vercel + Neon ready
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Vercel apne runtime mein VERCEL=1 set karta hai
IS_VERCEL = os.getenv('VERCEL') == '1'


# =============================================
# 🔐 SECURITY
# =============================================

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key-change-in-production')

DEBUG = os.getenv('DEBUG', 'False').strip().lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.getenv(
    'ALLOWED_HOSTS',
    "aqriculture-ticket-system-bggf.vercel.app",
    "localhost",
    "127.0.0.1",
).split(',')

if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Vercel khud HTTP -> HTTPS redirect karta hai, isliye wahan band rakho
    SECURE_SSL_REDIRECT = not IS_VERCEL
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
else:
    SECURE_HSTS_SECONDS = 0
    SECURE_SSL_REDIRECT = False


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
# 🗄️ DATABASE (Neon)
# =============================================

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=0,          # serverless: har request pe connection band
            ssl_require=not DEBUG,
        )
    }
    # Neon pooler (pgbouncer transaction mode) ke saath zaroori
    DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
else:
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

# Custom domain lagao to Vercel env mein CSRF_TRUSTED_ORIGINS add karna
CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:8000,http://127.0.0.1:8000,https://*.vercel.app'
).split(',')


# =============================================
# ⚡ CACHE
# =============================================

REDIS_URL = os.getenv('REDIS_URL')

if REDIS_URL:
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
    # Vercel pe har instance ka apna memory cache hota hai (instances ke beech share nahi hota)
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
    EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST          = 'smtp.gmail.com'
    EMAIL_PORT          = 587
    EMAIL_USE_TLS       = True
    EMAIL_HOST_USER     = os.getenv('EMAIL_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASSWORD')   # Gmail App Password
    DEFAULT_FROM_EMAIL  = os.getenv('EMAIL_USER')


# =============================================
# 📁 STATIC & MEDIA
# =============================================

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    d for d in [
        BASE_DIR / 'user' / 'static',
        BASE_DIR / 'static',
    ] if d.exists()
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise seedha app folders se static serve karega,
# isse Vercel pe collectstatic ke bharose nahi rehna padta
WHITENOISE_USE_FINDERS = True

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =============================================
# 🗃️ STORAGES
# =============================================

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY':    os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
}

STORAGES = {
    'default': {
        'BACKEND': (
            'django.core.files.storage.FileSystemStorage'
            if DEBUG
            else 'cloudinary_storage.storage.MediaCloudinaryStorage'
        ),
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}


# =============================================
# 📝 LOGGING (Vercel pe sirf console, file nahi)
# =============================================

_handlers = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'verbose',
    },
}
_active_handlers = ['console']

if not IS_VERCEL:
    LOGS_DIR = BASE_DIR / 'logs'
    LOGS_DIR.mkdir(exist_ok=True)
    _handlers['file'] = {
        'class':       'logging.handlers.RotatingFileHandler',
        'filename':    LOGS_DIR / 'django.log',
        'maxBytes':    1024 * 1024 * 5,
        'backupCount': 3,
        'formatter':   'verbose',
    }
    _active_handlers.append('file')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': _handlers,
    'loggers': {
        'django': {
            'handlers':  _active_handlers,
            'level':     'WARNING',
            'propagate': True,
        },
        'user': {
            'handlers':  _active_handlers,
            'level':     'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
    },
}


FAST2SMS_API_KEY = os.getenv('FAST2SMS_API_KEY')