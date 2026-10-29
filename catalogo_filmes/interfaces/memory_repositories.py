"""Adapters em memória: úteis para testes e para rodar sem MongoDB."""
from __future__ import annotations

from dataclasses import replace
from typing import List, Optional

from core.entities import Anuncio, Avaliacao, Filme, Ingresso, Usuario
from core.ports import (
    AnuncioRepository,
    AvaliacaoRepository,
    FilmeRepository,
    IngressoRepository,
    UsuarioRepository,
)


def aplicar_filtros(
    filmes: List[Filme],
    nome=None,
    categoria=None,
    classificacao=None,
    idade_max=None,
    duracao_max=None,
    nota_min=None,
) -> List[Filme]:
    resultado = []
    for f in filmes:
        if nome and nome.lower() not in f.nome.lower():
            continue
        if categoria and categoria.lower() not in f.categorias:
            continue
        if classificacao and f.classificacao != classificacao:
            continue
        if idade_max is not None and f.idade > idade_max:
            continue
        if duracao_max is not None and f.duracao > duracao_max:
            continue
        if nota_min is not None and f.avaliacao < nota_min:
            continue
        resultado.append(f)
    return resultado


class FilmeRepositoryMemoria(FilmeRepository):
    def __init__(self):
        self._dados: dict[str, Filme] = {}

    def salvar(self, filme: Filme) -> Filme:
        self._dados[filme.id] = filme
        return filme

    def obter(self, filme_id: str) -> Optional[Filme]:
        return self._dados.get(filme_id)

    def obter_por_tmdb_id(self, tmdb_id: int) -> Optional[Filme]:
        return next((f for f in self._dados.values() if f.tmdb_id == tmdb_id), None)

    def listar(self, limite: int = 20, offset: int = 0) -> List[Filme]:
        todos = sorted(self._dados.values(), key=lambda f: f.nome.lower())
        return todos[offset : offset + limite]

    def filtrar(self, limite: int = 20, offset: int = 0, **filtros) -> List[Filme]:
        todos = sorted(self._dados.values(), key=lambda f: f.nome.lower())
        return aplicar_filtros(todos, **filtros)[offset : offset + limite]


class UsuarioRepositoryMemoria(UsuarioRepository):
    def __init__(self):
        self._dados: dict[str, Usuario] = {}

    def salvar(self, usuario: Usuario) -> Usuario:
        self._dados[usuario.id] = usuario
        return usuario

    def obter(self, usuario_id: str) -> Optional[Usuario]:
        return self._dados.get(usuario_id)

    def obter_por_email(self, email: str) -> Optional[Usuario]:
        return next((u for u in self._dados.values() if u.email == email), None)


class AvaliacaoRepositoryMemoria(AvaliacaoRepository):
    def __init__(self):
        self._dados: dict[tuple, Avaliacao] = {}

    def salvar(self, avaliacao: Avaliacao) -> Avaliacao:
        self._dados[(avaliacao.filme_id, avaliacao.usuario_id)] = avaliacao
        return avaliacao

    def obter(self, filme_id: str, usuario_id: str) -> Optional[Avaliacao]:
        return self._dados.get((filme_id, usuario_id))

    def listar_por_filme(self, filme_id: str) -> List[Avaliacao]:
        return [a for (fid, _), a in self._dados.items() if fid == filme_id]


class AnuncioRepositoryMemoria(AnuncioRepository):
    def __init__(self):
        self._dados: dict[str, Anuncio] = {}

    def salvar(self, anuncio: Anuncio) -> Anuncio:
        self._dados[anuncio.id] = anuncio
        return anuncio

    def listar_ativos(self) -> List[Anuncio]:
        return [a for a in self._dados.values() if a.ativo]


class IngressoRepositoryMemoria(IngressoRepository):
    def __init__(self):
        self._dados: dict[str, Ingresso] = {}

    def salvar(self, ingresso: Ingresso) -> Ingresso:
        self._dados[ingresso.id] = ingresso
        return ingresso

    def listar_por_usuario(self, usuario_id: str) -> List[Ingresso]:
        return [i for i in self._dados.values() if i.usuario_id == usuario_id]
