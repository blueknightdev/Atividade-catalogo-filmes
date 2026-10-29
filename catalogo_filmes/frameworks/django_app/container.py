"""Composition root: único lugar que conhece todas as camadas e liga tudo."""
from __future__ import annotations

from types import SimpleNamespace

from django.conf import settings

from core import use_cases as uc
from interfaces import memory_repositories as mem
from interfaces.security import HashSenhaPBKDF2, TokenHMAC

_container = None


def _repositorios():
    if settings.DB_BACKEND == "mongo":
        from interfaces import mongo_repositories as mongo

        db = mongo.conectar(settings.MONGO_URI, settings.MONGO_DB)
        return SimpleNamespace(
            filmes=mongo.FilmeRepositoryMongo(db),
            usuarios=mongo.UsuarioRepositoryMongo(db),
            avaliacoes=mongo.AvaliacaoRepositoryMongo(db),
            anuncios=mongo.AnuncioRepositoryMongo(db),
            ingressos=mongo.IngressoRepositoryMongo(db),
        )
    return SimpleNamespace(
        filmes=mem.FilmeRepositoryMemoria(),
        usuarios=mem.UsuarioRepositoryMemoria(),
        avaliacoes=mem.AvaliacaoRepositoryMemoria(),
        anuncios=mem.AnuncioRepositoryMemoria(),
        ingressos=mem.IngressoRepositoryMemoria(),
    )


def _armazenamento():
    if settings.STORAGE_BACKEND == "s3":
        from interfaces.s3_storage import S3Storage

        return S3Storage(settings.S3_BUCKET, settings.AWS_REGION)
    from interfaces.s3_storage import ArmazenamentoLocal

    return ArmazenamentoLocal(pasta=str(settings.MEDIA_DIR), url_base="/media")


def get_container() -> SimpleNamespace:
    global _container
    if _container is not None:
        return _container

    repos = _repositorios()
    hasher = HashSenhaPBKDF2()
    tokens = TokenHMAC(settings.SECRET_KEY)
    arquivos = _armazenamento()

    catalogo = None
    if settings.TMDB_API_KEY:
        from interfaces.tmdb_client import TMDBClient

        catalogo = TMDBClient(settings.TMDB_API_KEY)

    _container = SimpleNamespace(
        cadastrar_usuario=uc.CadastrarUsuario(repos.usuarios, hasher),
        login=uc.Login(repos.usuarios, hasher, tokens),
        usuario_autenticado=uc.ObterUsuarioAutenticado(repos.usuarios, tokens),
        cadastrar_filme=uc.CadastrarFilme(repos.filmes),
        importar_tmdb=uc.ImportarFilmeDoTMDB(repos.filmes, catalogo, arquivos) if catalogo else None,
        listar_filmes=uc.ListarFilmes(repos.filmes),
        obter_filme=uc.ObterFilme(repos.filmes),
        filtrar_filmes=uc.FiltrarFilmes(repos.filmes),
        avaliar_filme=uc.AvaliarFilme(repos.filmes, repos.avaliacoes),
        listar_avaliacoes=uc.ListarAvaliacoes(repos.avaliacoes),
        comprar_ingresso=uc.ComprarIngresso(repos.filmes, repos.ingressos, settings.PRECO_INGRESSO),
        meus_ingressos=uc.ListarMeusIngressos(repos.ingressos),
        criar_anuncio=uc.CriarAnuncio(repos.anuncios, repos.filmes),
        listar_anuncios=uc.ListarAnuncios(repos.anuncios),
    )
    if settings.DB_BACKEND == "memory" and settings.SEED_DEMO:
        _semear(_container)
    return _container


def _semear(c: SimpleNamespace) -> None:
    """Dados de demonstração para o modo em memória (somem ao reiniciar)."""
    admin = c.cadastrar_usuario.executar("Admin Demo", "admin@demo.com", "admin123", 30, is_admin=True)
    ana = c.cadastrar_usuario.executar("Ana Demo", "ana@demo.com", "demo123", 17)
    c.cadastrar_usuario.executar("Davi Demo", "davi@demo.com", "demo123", 25)

    filmes = [
        dict(nome="Viagem às Estrelas", duracao=128, idade=12, categorias=["Ficção", "Aventura"],
             sinopse="Uma tripulação cruza a galáxia em busca de um novo lar para a humanidade."),
        dict(nome="O Último Samba", duracao=102, idade=0, categorias=["Drama", "Musical"],
             sinopse="Um sambista veterano reúne a velha guarda para uma última roda no Rio."),
        dict(nome="Noite sem Fim", duracao=117, idade=18, categorias=["Terror", "Suspense"],
             sinopse="Uma cidade onde o sol não nasce há três dias e ninguém sabe por quê."),
        dict(nome="Turma da Floresta", duracao=84, idade=0, categorias=["Animação", "Família"],
             sinopse="Bichos da mata se unem para salvar o rio que abastece a floresta."),
        dict(nome="Corrida Final", duracao=139, idade=14, categorias=["Ação", "Esporte"],
             sinopse="Um piloto aposentado volta às pistas para disputar o título que lhe escapou."),
    ]
    criados = [c.cadastrar_filme.executar(admin, **dados) for dados in filmes]
    for filme, nota in zip(criados, (9, 8, 7, 9.5, 8.5)):
        c.avaliar_filme.executar(ana, filme.id, nota, "Gostei bastante!")
    c.criar_anuncio.executar(admin, "Estreia: Viagem às Estrelas — compre seu ingresso!", filme_id=criados[0].id)


def resetar_container():
    """Usado nos testes para começar do zero."""
    global _container
    _container = None
