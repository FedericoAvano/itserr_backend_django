from pathlib import Path
import os
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- RILEVAMENTO DELL'AMBIENTE ---
# Imposta l'ambiente di default su 'development'.
# In produzione, dovrai impostare la variabile d'ambiente DJANGO_ENV a 'production'.
ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')

# Impostazioni condizionali basate sull'ambiente
if ENVIRONMENT == 'production':
    DEBUG = False
    ALLOWED_HOSTS = ['il_tuo_dominio.com', 'www.il_tuo_dominio.com']
else:
    DEBUG = True
    ALLOWED_HOSTS = []

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-ui5=@7$820z#^6ww3ghxl&pwb_2550+qljo=!ix2i56)8&(o$z'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'api',
    'channels',
    'corsheaders',
    'django_filters',
    'django_cleanup.apps.CleanupConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # 👈 In cima per gestire i problemi di CORS in sviluppo
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'itserr_backend_django.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'itserr_backend_django.wsgi.application'
ASGI_APPLICATION = 'itserr_backend_django.asgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 60,  # SQLite aspetterà fino a 60 secondi prima di generare l'errore 'locked'
        }
    }
}

CORS_ALLOW_ALL_ORIGINS = True

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static & Media Files
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Channels / Redis Configuration
# Assicurati che Redis sia in esecuzione sulla porta 6379
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}

# --- CONFIGURAZIONE REST FRAMEWORK ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',   # 👈 Riconosce il Token negli Header
        'rest_framework.authentication.SessionAuthentication',  # 👈 Mantiene l'accesso al Django Admin classico
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly', # 👈 Tutti leggono, solo gli admin autenticati scrivono
    ],
}

# =========================================================================
# ⚠️ CONFIGURAZIONE LIMITI DI CARICAMENTO MASSIVO (NUOVO)
# =========================================================================
# Massima dimensione in byte della richiesta HTTP (es. 2.5 GB)
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800



# Rimuove il limite del numero di parametri massimi caricabili (utile per i form complessi)
DATA_UPLOAD_MAX_NUMBER_FIELDS = None


