"""Configuração do Django (camada FRAMEWORKS E DRIVERS).

Não usamos o ORM do Django: a persistência é feita pelos adapters (MongoDB).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"
MEDIA_DIR = BASE_DIR / "media"  # pôsteres quando STORAGE_BACKEND=local

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-inseguro-troque-em-producao")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

ROOT_URLCONF = "frameworks.django_app.urls"
INSTALLED_APPS = []
MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]
DATABASES = {}
USE_TZ = True
TIME_ZONE = "America/Sao_Paulo"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Backends escolhidos na composição (ver container.py) ---
DB_BACKEND = os.environ.get("DB_BACKEND", "memory")  # memory | mongo
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "catalogo_filmes")

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")  # local | s3
S3_BUCKET = os.environ.get("S3_BUCKET", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

ADMIN_EMAILS = [e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()]

# Dados de demonstração (só vale com DB_BACKEND=memory): cria filmes, anúncio e contas de teste
SEED_DEMO = os.environ.get("SEED_DEMO", "1") == "1"

PRECO_INGRESSO = float(os.environ.get("PRECO_INGRESSO", "30.0"))
