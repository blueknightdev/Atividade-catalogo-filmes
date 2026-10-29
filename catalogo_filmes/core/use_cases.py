"""Camada 2 — CASOS DE USO.

Um caso de uso para cada item do diagrama:
  CADASTRAR FILME, ANÚNCIOS, VENDA DE INGRESSOS, FILTRAR FILMES,
  LISTAR FILMES, AVALIAR FILME, LOGIN E CADASTRO.
"""
from __future__ import annotations

from typing import List, Optional

from .entities import Anuncio, Avaliacao, Filme, Ingresso, Usuario
from .exceptions import (
    DadosInvalidos,
    IdadeInsuficiente,
    JaExiste,
    NaoAutenticado,
    NaoAutorizado,
    NaoEncontrado,
)
from .ports import (
    AnuncioRepository,
    ArmazenamentoArquivos,
    AvaliacaoRepository,
    CatalogoExterno,
    FilmeRepository,
    HashSenha,
    IngressoRepository,
    TokenService,
    UsuarioRepository,
)


# --------------------------------------------------------------------------- #
# LOGIN E CADASTRO
# --------------------------------------------------------------------------- #
class CadastrarUsuario:
    def __init__(self, usuarios: UsuarioRepository, hasher: HashSenha):
        self.usuarios = usuarios
        self.hasher = hasher

    def executar(self, nome: str, email: str, senha: str, idade: int, is_admin: bool = False) -> Usuario:
        if not senha or len(senha) < 6:
            raise DadosInvalidos("A senha deve ter pelo menos 6 caracteres.")
        if self.usuarios.obter_por_email((email or "").strip().lower()):
            raise JaExiste("Já existe um usuário com esse e-mail.")
        usuario = Usuario(nome=nome, email=email, senha_hash=self.hasher.gerar(senha), idade=idade, is_admin=is_admin)
        return self.usuarios.salvar(usuario)


class Login:
    def __init__(self, usuarios: UsuarioRepository, hasher: HashSenha, tokens: TokenService):
        self.usuarios = usuarios
        self.hasher = hasher
        self.tokens = tokens

    def executar(self, email: str, senha: str) -> tuple[str, Usuario]:
        usuario = self.usuarios.obter_por_email((email or "").strip().lower())
        if not usuario or not self.hasher.verificar(senha or "", usuario.senha_hash):
            raise NaoAutenticado("E-mail ou senha incorretos.")
        return self.tokens.emitir(usuario.id), usuario


class ObterUsuarioAutenticado:
    def __init__(self, usuarios: UsuarioRepository, tokens: TokenService):
        self.usuarios = usuarios
        self.tokens = tokens

    def executar(self, token: Optional[str]) -> Usuario:
        usuario_id = self.tokens.validar(token or "")
        usuario = self.usuarios.obter(usuario_id) if usuario_id else None
        if not usuario:
            raise NaoAutenticado("Token ausente ou inválido.")
        return usuario


# --------------------------------------------------------------------------- #
# CADASTRAR FILME
# --------------------------------------------------------------------------- #
class CadastrarFilme:
    """Cadastro manual de um filme (somente administradores)."""

    def __init__(self, filmes: FilmeRepository):
        self.filmes = filmes

    def executar(
        self,
        admin: Usuario,
        nome: str,
        duracao: int,
        idade: int = 0,
        categorias: Optional[List[str]] = None,
        classificacao: str = "",
        sinopse: str = "",
        poster_url: str = "",
    ) -> Filme:
        if not admin.is_admin:
            raise NaoAutorizado("Apenas administradores podem cadastrar filmes.")
        filme = Filme(
            nome=nome,
            duracao=duracao,
            idade=idade,
            categorias=categorias or [],
            classificacao=classificacao,
            sinopse=sinopse,
            poster_url=poster_url,
        )
        return self.filmes.salvar(filme)


class ImportarFilmeDoTMDB:
    """Cadastra um filme a partir do TMDB e guarda o pôster no S3."""

    def __init__(self, filmes: FilmeRepository, catalogo: CatalogoExterno, arquivos: ArmazenamentoArquivos):
        self.filmes = filmes
        self.catalogo = catalogo
        self.arquivos = arquivos

    def executar(self, admin: Usuario, tmdb_id: int) -> Filme:
        if not admin.is_admin:
            raise NaoAutorizado("Apenas administradores podem importar filmes.")
        existente = self.filmes.obter_por_tmdb_id(tmdb_id)
        if existente:
            raise JaExiste("Esse filme do TMDB já foi importado.")
        dados = self.catalogo.buscar_filme(tmdb_id)
        poster = dados.get("poster_url", "")
        if poster:
            try:
                poster = self.arquivos.salvar_url_remota(poster, f"posters/tmdb-{tmdb_id}.jpg")
            except Exception:
                pass  # mantém a URL original do TMDB se o S3 falhar
        filme = Filme(
            nome=dados["nome"],
            duracao=dados.get("duracao") or 1,
            idade=dados.get("idade", 0),
            categorias=dados.get("categorias", []),
            sinopse=dados.get("sinopse", ""),
            poster_url=poster,
            tmdb_id=tmdb_id,
        )
        return self.filmes.salvar(filme)


# --------------------------------------------------------------------------- #
# LISTAR FILMES / FILTRAR FILMES
# --------------------------------------------------------------------------- #
class ListarFilmes:
    def __init__(self, filmes: FilmeRepository):
        self.filmes = filmes

    def executar(self, limite: int = 20, offset: int = 0) -> List[Filme]:
        return self.filmes.listar(limite=_limite(limite), offset=max(0, offset))


class ObterFilme:
    def __init__(self, filmes: FilmeRepository):
        self.filmes = filmes

    def executar(self, filme_id: str) -> Filme:
        filme = self.filmes.obter(filme_id)
        if not filme:
            raise NaoEncontrado("Filme não encontrado.")
        return filme


class FiltrarFilmes:
    def __init__(self, filmes: FilmeRepository):
        self.filmes = filmes

    def executar(self, limite: int = 20, offset: int = 0, **filtros) -> List[Filme]:
        if filtros.get("categoria"):
            filtros["categoria"] = filtros["categoria"].strip().lower()
        return self.filmes.filtrar(limite=_limite(limite), offset=max(0, offset), **filtros)


def _limite(valor: int) -> int:
    return max(1, min(int(valor), 100))


# --------------------------------------------------------------------------- #
# AVALIAR FILME
# --------------------------------------------------------------------------- #
class AvaliarFilme:
    """Cria ou atualiza a avaliação de um usuário e recalcula a média do filme."""

    def __init__(self, filmes: FilmeRepository, avaliacoes: AvaliacaoRepository):
        self.filmes = filmes
        self.avaliacoes = avaliacoes

    def executar(self, usuario: Usuario, filme_id: str, nota: float, comentario: str = "") -> Avaliacao:
        filme = self.filmes.obter(filme_id)
        if not filme:
            raise NaoEncontrado("Filme não encontrado.")
        anterior = self.avaliacoes.obter(filme_id, usuario.id)
        if anterior:
            nota_antiga = anterior.nota
            anterior.nota = Avaliacao(filme_id, usuario.id, nota).nota  # valida a nova nota
            anterior.comentario = comentario
            avaliacao = anterior
            filme.registrar_nota(avaliacao.nota, nota_anterior=nota_antiga)
        else:
            avaliacao = Avaliacao(filme_id=filme_id, usuario_id=usuario.id, nota=nota, comentario=comentario)
            filme.registrar_nota(avaliacao.nota)
        self.avaliacoes.salvar(avaliacao)
        self.filmes.salvar(filme)
        return avaliacao


class ListarAvaliacoes:
    def __init__(self, avaliacoes: AvaliacaoRepository):
        self.avaliacoes = avaliacoes

    def executar(self, filme_id: str) -> List[Avaliacao]:
        return self.avaliacoes.listar_por_filme(filme_id)


# --------------------------------------------------------------------------- #
# VENDA DE INGRESSOS
# --------------------------------------------------------------------------- #
class ComprarIngresso:
    def __init__(self, filmes: FilmeRepository, ingressos: IngressoRepository, preco_unitario: float = 30.0):
        self.filmes = filmes
        self.ingressos = ingressos
        self.preco_unitario = preco_unitario

    def executar(self, usuario: Usuario, filme_id: str, quantidade: int = 1) -> Ingresso:
        filme = self.filmes.obter(filme_id)
        if not filme:
            raise NaoEncontrado("Filme não encontrado.")
        if not filme.permitido_para(usuario.idade):
            raise IdadeInsuficiente(
                f"Este filme exige idade mínima de {filme.idade} anos (classificação {filme.classificacao})."
            )
        ingresso = Ingresso(
            filme_id=filme_id,
            usuario_id=usuario.id,
            quantidade=quantidade,
            valor_total=round(self.preco_unitario * int(quantidade), 2),
        )
        return self.ingressos.salvar(ingresso)


class ListarMeusIngressos:
    def __init__(self, ingressos: IngressoRepository):
        self.ingressos = ingressos

    def executar(self, usuario: Usuario) -> List[Ingresso]:
        return self.ingressos.listar_por_usuario(usuario.id)


# --------------------------------------------------------------------------- #
# ANÚNCIOS
# --------------------------------------------------------------------------- #
class CriarAnuncio:
    def __init__(self, anuncios: AnuncioRepository, filmes: FilmeRepository):
        self.anuncios = anuncios
        self.filmes = filmes

    def executar(
        self, admin: Usuario, titulo: str, imagem_url: str = "", link: str = "", filme_id: Optional[str] = None
    ) -> Anuncio:
        if not admin.is_admin:
            raise NaoAutorizado("Apenas administradores podem criar anúncios.")
        if filme_id and not self.filmes.obter(filme_id):
            raise NaoEncontrado("Filme do anúncio não encontrado.")
        return self.anuncios.salvar(Anuncio(titulo=titulo, imagem_url=imagem_url, link=link, filme_id=filme_id))


class ListarAnuncios:
    def __init__(self, anuncios: AnuncioRepository):
        self.anuncios = anuncios

    def executar(self) -> List[Anuncio]:
        return self.anuncios.listar_ativos()
