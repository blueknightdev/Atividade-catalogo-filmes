from django.conf import settings
from django.urls import path, re_path
from django.views.static import serve

from . import views

urlpatterns = [
    # Front end (frontend/) e arquivos enviados (media/)
    path("", views.index),
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.FRONTEND_DIR}),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_DIR}),
    # API
    path("api/cadastro/", views.cadastro),
    path("api/login/", views.login),
    path("api/filmes/", views.filmes),
    path("api/filmes/importar-tmdb/", views.importar_tmdb),
    path("api/filmes/<str:filme_id>/", views.filme_detalhe),
    path("api/filmes/<str:filme_id>/avaliacoes/", views.avaliacoes),
    path("api/ingressos/", views.ingressos),
    path("api/anuncios/", views.anuncios),
]
