import os
from pathlib import Path

# ================================
# BASE DIRECTORY
# ================================
BASE_DIR = Path(__file__).resolve().parent.parent


# ================================
# BASIC SETTINGS
# ================================
SECRET_KEY = "HWuyNCqgEXrv7t8reeM1DW8VvduOGwkabtlC7pHLg-q_uQS_gBDMy3l6qeCHf46NfG8"

DEBUG = True  # Production

ALLOWED_HOSTS = [
    "api.matchb.online",
    "31.97.229.150",
    "localhost",
]

CSRF_TRUSTED_ORIGINS = [
    "https://api.matchb.online",
    "https://31.97.229.150",
]


# ================================
# INSTALLED APPS
# ================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "import_export",
    "widget_tweaks",

    # Local apps
    "master.apps.MasterConfig",
    "users.apps.UsersConfig",
    "po.apps.PoConfig",
    "bom.apps.BomConfig",
    "indent.apps.IndentConfig",
]


# ================================
# MIDDLEWARE
# ================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # Whitenoise MUST be here (directly after SecurityMiddleware)
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ================================
# URLS & WSGI
# ================================
ROOT_URLCONF = "suntech_erp.urls"
WSGI_APPLICATION = "suntech_erp.wsgi.application"


# ================================
# DATABASE (MySQL)
# ================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "suntech_db",
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


# ================================
# TEMPLATES
# ================================
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


# ================================
# PASSWORD VALIDATION
# ================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ================================
# LANGUAGE & TIMEZONE
# ================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True


# ================================
# STATIC FILES (Whitenoise)
# ================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Whitenoise static file handling
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# ================================
# MEDIA FILES
# ================================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ================================
# CUSTOM USER MODEL
# ================================
AUTH_USER_MODEL = "users.CustomUser"


# ================================
# LOGIN REDIRECTS
# ================================
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "users:login"
LOGIN_URL = "users:login"

IMPORT_EXPORT_USE_TRANSACTIONS = True


# ================================
# EMAIL (CONSOLE OR SMTP)
# ================================
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# ================================
# SECURITY HEADERS
# ================================
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True


# ================================
# LOGGING
# ================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs/django.log",
        },
        "console": {
            "class": "logging.StreamHandler",
        }
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        }
    }
}
