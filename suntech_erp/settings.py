import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "HWuyNCqgEXrv7t8reeM1DW8VvduOGwkabtlC7pHLg-q_uQS_gBDMy3l6qeCHf46NfG8"

DEBUG = True  # Development mode

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = ["http://*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "import_export",
    "widget_tweaks",
    "master.apps.MasterConfig",
    "users.apps.UsersConfig",
    "po.apps.PoConfig",
    "bom.apps.BomConfig",
    "indent.apps.IndentConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "suntech_erp.urls"
WSGI_APPLICATION = "suntech_erp.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "suntech_db_2",
        "USER": "root",
        "PASSWORD": "",
        "HOST": "localhost",
        "PORT": "3306",
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            "charset": "utf8mb4",
        },
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# ❗ Disable compressed staticfiles storage for dev
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

AUTH_USER_MODEL = "users.CustomUser"

LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "users:login"
LOGIN_URL = "users:login"

IMPORT_EXPORT_USE_TRANSACTIONS = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ========================================
# ❗ ALL PRODUCTION SECURITY SETTINGS OFF
# ========================================

# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# ========================================
# LOGGING (ONLY CONSOLE FOR DEV)
# ========================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
        # ❗ Comment out file logging to avoid missing folder errors
        # "file": {
        #     "level": "INFO",
        #     "class": "logging.FileHandler",
        #     "filename": BASE_DIR / "logs/django.log",
        # },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],  # Only console in dev
            "level": "INFO",
            "propagate": True,
        }
    }
}
