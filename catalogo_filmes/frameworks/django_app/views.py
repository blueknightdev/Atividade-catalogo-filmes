"""Views JSON do Django. Só traduzem HTTP <-> casos de uso."""
from __future__ import annotations

import json
from dataclasses import asdict
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from core import exceptions as exc

from .container import get_container

STATUS = {
    exc.DadosInvalidos: 400,
    exc.NaoAutenticado: 401,
    exc.NaoAutorizado: 403,
    exc.IdadeInsuficiente: 403,
    exc.NaoEncontrado: 404,
    exc.JaExiste: 409,
}


def _serializar(obj):
    d = asdict(obj)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    d.pop("senha_hash", None)
    return d


def api(view):
    """Decorator: converte exceções de domínio em respostas JSON."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except exc.ErroDeDominio as e:
            return JsonResponse({"erro": str(e)}, status=STATUS.get(type(e), 400))
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido."}, status=400)

    return wrapper


def _body(request) -> dict:
    return json.loads(request.body or b"{}")


def _usuario(request):
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else None
    return get_container().usuario_autenticado.executar(token)


def _int(request, nome, padrao=None):
    valor = request.GET.get(nome)
    return int(valor) if valor not in (None, "") else padrao


def _float(request, nome):
    valor = request.GET.get(nome)
    return float(valor) if valor not in (None, "") else None


def index(request):
    """Entrega a página única do front end."""
    from django.views.static import serve

    return serve(request, "index.html", document_root=settings.FRONTEND_DIR)


# ----------------------------- LOGIN E CADASTRO ----------------------------- #
@csrf_exempt
@require_POST
@api
def cadastro(request):
    d = _body(request)
    email = (d.get("email") or "").strip().lower()
    usuario = get_container().cadastrar_usuario.executar(
        nome=d.get("nome", ""),
        email=email,
        senha=d.get("senha", ""),
        idade=d.get("idade", 0),
        is_admin=email in settings.ADMIN_EMAILS,  # admins definidos por variável de ambiente
    )
    return JsonResponse(_serializar(usuario), status=201)


@csrf_exempt
@require_POST
@api
def login(request):
    d = _body(request)
    token, usuario = get_container().login.executar(d.get("email", ""), d.get("senha", ""))
    return JsonResponse({"token": token, "usuario": _serializar(usuario)})


# ------------------------- LISTAR / FILTRAR / CADASTRAR --------------------- #
@csrf_exempt
@require_http_methods(["GET", "POST"])
@api
def filmes(request):
    c = get_container()
    if request.method == "POST":
        admin = _usuario(request)
        d = _body(request)
        filme = c.cadastrar_filme.executar(
            admin,
            nome=d.get("nome", ""),
            duracao=d.get("duracao", 0),
            idade=d.get("idade", 0),
            categorias=d.get("categorias", []),
            classificacao=d.get("classificacao", ""),
            sinopse=d.get("sinopse", ""),
            poster_url=d.get("poster_url", ""),
        )
        return JsonResponse(_serializar(filme), status=201)

    limite, offset = _int(request, "limite", 20), _int(request, "offset", 0)
    filtros = {
        "nome": request.GET.get("nome") or None,
        "categoria": request.GET.get("categoria") or None,
        "classificacao": request.GET.get("classificacao") or None,
        "idade_max": _int(request, "idade_max"),
        "duracao_max": _int(request, "duracao_max"),
        "nota_min": _float(request, "nota_min"),
    }
    if any(v is not None for v in filtros.values()):
        lista = c.filtrar_filmes.executar(limite=limite, offset=offset, **filtros)
    else:
        lista = c.listar_filmes.executar(limite=limite, offset=offset)
    return JsonResponse({"resultados": [_serializar(f) for f in lista]})


@require_GET
@api
def filme_detalhe(request, filme_id):
    return JsonResponse(_serializar(get_container().obter_filme.executar(filme_id)))


@csrf_exempt
@require_POST
@api
def importar_tmdb(request):
    c = get_container()
    if c.importar_tmdb is None:
        return JsonResponse({"erro": "TMDB_API_KEY não configurada."}, status=503)
    admin = _usuario(request)
    filme = c.importar_tmdb.executar(admin, int(_body(request).get("tmdb_id", 0)))
    return JsonResponse(_serializar(filme), status=201)


# ------------------------------- AVALIAR FILME ------------------------------ #
@csrf_exempt
@require_http_methods(["GET", "POST"])
@api
def avaliacoes(request, filme_id):
    c = get_container()
    if request.method == "POST":
        usuario = _usuario(request)
        d = _body(request)
        a = c.avaliar_filme.executar(usuario, filme_id, d.get("nota"), d.get("comentario", ""))
        return JsonResponse(_serializar(a), status=201)
    c.obter_filme.executar(filme_id)
    return JsonResponse({"resultados": [_serializar(a) for a in c.listar_avaliacoes.executar(filme_id)]})


# ----------------------------- VENDA DE INGRESSOS --------------------------- #
@csrf_exempt
@require_http_methods(["GET", "POST"])
@api
def ingressos(request):
    c = get_container()
    usuario = _usuario(request)
    if request.method == "POST":
        d = _body(request)
        ing = c.comprar_ingresso.executar(usuario, d.get("filme_id", ""), d.get("quantidade", 1))
        return JsonResponse(_serializar(ing), status=201)
    return JsonResponse({"resultados": [_serializar(i) for i in c.meus_ingressos.executar(usuario)]})


# ---------------------------------- ANÚNCIOS -------------------------------- #
@csrf_exempt
@require_http_methods(["GET", "POST"])
@api
def anuncios(request):
    c = get_container()
    if request.method == "POST":
        admin = _usuario(request)
        d = _body(request)
        a = c.criar_anuncio.executar(
            admin, d.get("titulo", ""), d.get("imagem_url", ""), d.get("link", ""), d.get("filme_id")
        )
        return JsonResponse(_serializar(a), status=201)
    return JsonResponse({"resultados": [_serializar(a) for a in c.listar_anuncios.executar()]})
