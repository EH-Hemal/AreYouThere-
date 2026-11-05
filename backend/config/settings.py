import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / '.env')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'development-only-change-before-deployment')
DEBUG = os.getenv('DEBUG', '1') == '1'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
INSTALLED_APPS = ['daphne', 'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'rest_framework', 'rest_framework.authtoken', 'corsheaders', 'core']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'corsheaders.middleware.CorsMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
ASGI_APPLICATION = 'config.asgi.application'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
DATABASES = {'default': {'ENGINE':'django.db.backends.mysql','NAME':os.getenv('MYSQL_DATABASE','areyouthere'),'USER':os.getenv('MYSQL_USER','areyouthere_app'),'PASSWORD':os.getenv('MYSQL_PASSWORD',''),'HOST':os.getenv('MYSQL_HOST','127.0.0.1'),'PORT':os.getenv('MYSQL_PORT','3306'),'OPTIONS':{'charset':'utf8mb4','connect_timeout':5,'init_command':"SET sql_mode='STRICT_TRANS_TABLES'"},'TEST':{'NAME':'test_areyouthere'}}}
AUTH_USER_MODEL = 'core.User'
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES':['core.auth.ExpiringTokenAuthentication'],'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.IsAuthenticated'],'DEFAULT_THROTTLE_CLASSES':['rest_framework.throttling.AnonRateThrottle','rest_framework.throttling.UserRateThrottle'],'DEFAULT_THROTTLE_RATES':{'anon':'60/min','user':'600/min','auth':'10/min'}}
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(',')
CORS_ALLOWED_ORIGIN_REGEXES = [r'^chrome-extension://[a-p]{32}$'] if DEBUG else []
CSRF_TRUSTED_ORIGINS = [origin for origin in CORS_ALLOWED_ORIGINS if origin.startswith(('http://','https://'))]
CHANNEL_LAYERS = {'default':{'BACKEND':'channels_redis.core.RedisChannelLayer','CONFIG':{'hosts':[os.getenv('REDIS_URL','redis://127.0.0.1:6379/0')],'capacity':1000,'expiry':30}}}
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
if not DEBUG:
    if SECRET_KEY == 'development-only-change-before-deployment':
        raise RuntimeError('Set DJANGO_SECRET_KEY for production')
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

