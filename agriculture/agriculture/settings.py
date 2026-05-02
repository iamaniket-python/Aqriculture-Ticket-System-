"""
Django settings for agriculture project — Production Ready
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

# .env file load karo
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================
# 🔐 SECURITY
# =============================================

SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


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
]

# =============================================
# 🔧 MIDDLEWARE
# =============================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'user.context_processors.admin_notifications',
                'user.context_processors.staff_notifications'
            ],
        },
    },
]

WSGI_APPLICATION = 'agriculture.wsgi.application'


# =============================================
# 🗄️ DATABASE
# =============================================

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.getenv('DB_NAME'),
        'USER':     os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST':     os.getenv('DB_HOST', 'localhost'),
        'PORT':     os.getenv('DB_PORT', '5432'),
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

SESSION_COOKIE_NAME      = 'main_session'
SESSION_COOKIE_SAMESITE  = 'Lax'
SESSION_COOKIE_HTTPONLY  = True
SESSION_COOKIE_SECURE    = not DEBUG   # Production mein True, Dev mein False
SESSION_COOKIE_AGE       = 86400
SESSION_SAVE_EVERY_REQUEST  = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_ENGINE           = 'django.contrib.sessions.backends.db'


# =============================================
# 🛡️ CSRF SETTINGS
# =============================================

CSRF_COOKIE_SAMESITE  = 'Lax'
CSRF_COOKIE_HTTPONLY  = False
CSRF_COOKIE_SECURE    = not DEBUG   # Production mein True


# =============================================
# ⚡ CACHE — OTP store ke liye
# =============================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
# Production mein Redis use karo:
# pip install django-redis
# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": "redis://127.0.0.1:6379/1",
#     }
# }


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
    'BLACKLIST_AFTER_ROTATION': True,   # Old tokens blacklist ho jaayein
    'AUTH_HEADER_TYPES':        ('Bearer',),
}


# =============================================
# 🌍 INTERNATIONALIZATION
# =============================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'   # ✅ India timezone
USE_I18N      = True
USE_TZ        = True


# =============================================
# 📧 EMAIL
# =============================================

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Production mein:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = os.getenv('EMAIL_USER')
# EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASSWORD')


# =============================================
# 📁 STATIC & MEDIA
# =============================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'user' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'   # collectstatic yahan save karega

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =============================================
# 📝 LOGGING
# =============================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'user': {
            'handlers':  ['console'],
            'level':     'DEBUG' if DEBUG else 'WARNING',
            'propagate': True,
        },
    },
}