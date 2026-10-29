"""Portas (interfaces abstratas) que os casos de uso precisam.

Quem implementa essas portas são os adapters da camada INTERFACE.
Assim os casos de uso nunca dependem de MongoDB, TMDB, S3 ou Django.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import Anuncio, Avaliacao, Filme, Ingresso, Usuario


class FilmeRepository(ABC):
    @abstractmethod
    def salvar(self, filme: Filme) -> Filme: ...

    @abstractmethod
    def obter(self, filme_id: str) -> Optional[Filme]: ...

    @abstractmethod
    def obter_por_tmdb_id(self, tmdb_id: int) -> Optional[Filme]: ...

    @abstractmethod
    def listar(self, limite: int = 20, offset: int = 0) -> List[Filme]: ...

    @abstractmethod
    def filtrar(
        self,
        nome: Optional[str] = None,
        categoria: Optional[str] = None,
        classificacao: Optional[str] = None,
        idade_max: Optional[int] = None,
        duracao_max: Optional[int] = None,
        nota_min: Optional[float] = None,
        limite: int = 20,
        offset: int = 0,
    ) -> List[Filme]: ...


class UsuarioRepository(ABC):
    @abstractmethod
    def salvar(self, usuario: Usuario) -> Usuario: ...

    @abstractmethod
    def obter(self, usuario_id: str) -> Optional[Usuario]: ...

    @abstractmethod
    def obter_por_email(self, email: str) -> Optional[Usuario]: ...


class AvaliacaoRepository(ABC):
    @abstractmethod
    def salvar(self, avaliacao: Avaliacao) -> Avaliacao: ...

    @abstractmethod
    def obter(self, filme_id: str, usuario_id: str) -> Optional[Avaliacao]: ...

    @abstractmethod
    def listar_por_filme(self, filme_id: str) -> List[Avaliacao]: ...


class AnuncioRepository(ABC):
    @abstractmethod
    def salvar(self, anuncio: Anuncio) -> Anuncio: ...

    @abstractmethod
    def listar_ativos(self) -> List[Anuncio]: ...


class IngressoRepository(ABC):
    @abstractmethod
    def salvar(self, ingresso: Ingresso) -> Ingresso: ...

    @abstractmethod
    def listar_por_usuario(self, usuario_id: str) -> List[Ingresso]: ...


class CatalogoExterno(ABC):
    """Fonte externa de dados de filmes (TMDB)."""

    @abstractmethod
    def buscar_filme(self, tmdb_id: int) -> dict:
        """Retorna dict com: nome, duracao, categorias, idade, sinopse, poster_url, poster_origem."""


class ArmazenamentoArquivos(ABC):
    """Armazenamento de arquivos (Amazon S3)."""

    @abstractmethod
    def salvar_url_remota(self, url: str, chave: str) -> str:
        """Baixa a imagem da URL, guarda e devolve a URL pública final."""

    @abstractmethod
    def salvar_bytes(self, dados: bytes, chave: str, content_type: str) -> str: ...


class HashSenha(ABC):
    @abstractmethod
    def gerar(self, senha: str) -> str: ...

    @abstractmethod
    def verificar(self, senha: str, hash_: str) -> bool: ...


class TokenService(ABC):
    @abstractmethod
    def emitir(self, usuario_id: str) -> str: ...

    @abstractmethod
    def validar(self, token: str) -> Optional[str]:
        """Devolve o usuario_id se o token for válido, senão None."""
