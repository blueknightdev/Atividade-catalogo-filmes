"""Adapters MongoDB (pymongo). O import é feito aqui, nunca no core."""
from __future__ import annotations

import re
from dataclasses import asdict
from typing import List, Optional

from core.entities import Anuncio, Avaliacao, Filme, Ingresso, Usuario
from core.ports import (
    AnuncioRepository,
    AvaliacaoRepository,
    FilmeRepository,
    IngressoRepository,
    UsuarioRepository,
)


def conectar(uri: str, nome_db: str):
    from pymongo import MongoClient  # import tardio: só exigido quando MongoDB é usado

    db = MongoClient(uri)[nome_db]
    db.filmes.create_index("tmdb_id", sparse=True)
    db.filmes.create_index("categorias")
    db.usuarios.create_index("email", unique=True)
    db.avaliacoes.create_index([("filme_id", 1), ("usuario_id", 1)], unique=True)
    return db


def _para_doc(obj) -> dict:
    doc = asdict(obj)
    doc["_id"] = doc.pop("id")
    return doc


def _de_doc(cls, doc: Optional[dict]):
    if doc is None:
        return None
    doc = dict(doc)
    doc["id"] = doc.pop("_id")
    return cls(**doc)


class FilmeRepositoryMongo(FilmeRepository):
    def __init__(self, db):
        self.col = db.filmes

    def salvar(self, filme: Filme) -> Filme:
        self.col.replace_one({"_id": filme.id}, _para_doc(filme), upsert=True)
        return filme

    def obter(self, filme_id: str) -> Optional[Filme]:
        return _de_doc(Filme, self.col.find_one({"_id": filme_id}))

    def obter_por_tmdb_id(self, tmdb_id: int) -> Optional[Filme]:
        return _de_doc(Filme, self.col.find_one({"tmdb_id": tmdb_id}))

    def listar(self, limite: int = 20, offset: int = 0) -> List[Filme]:
        cursor = self.col.find().sort("nome", 1).skip(offset).limit(limite)
        return [_de_doc(Filme, d) for d in cursor]

    def filtrar(
        self,
        nome=None,
        categoria=None,
        classificacao=None,
        idade_max=None,
        duracao_max=None,
        nota_min=None,
        limite: int = 20,
        offset: int = 0,
    ) -> List[Filme]:
        q: dict = {}
        if nome:
            q["nome"] = {"$regex": re.escape(nome), "$options": "i"}
        if categoria:
            q["categorias"] = categoria.lower()
        if classificacao:
            q["classificacao"] = classificacao
        if idade_max is not None:
            q["idade"] = {"$lte": idade_max}
        if duracao_max is not None:
            q["duracao"] = {"$lte": duracao_max}
        if nota_min is not None:
            q["avaliacao"] = {"$gte": nota_min}
        cursor = self.col.find(q).sort("nome", 1).skip(offset).limit(limite)
        return [_de_doc(Filme, d) for d in cursor]


class UsuarioRepositoryMongo(UsuarioRepository):
    def __init__(self, db):
        self.col = db.usuarios

    def salvar(self, usuario: Usuario) -> Usuario:
        self.col.replace_one({"_id": usuario.id}, _para_doc(usuario), upsert=True)
        return usuario

    def obter(self, usuario_id: str) -> Optional[Usuario]:
        return _de_doc(Usuario, self.col.find_one({"_id": usuario_id}))

    def obter_por_email(self, email: str) -> Optional[Usuario]:
        return _de_doc(Usuario, self.col.find_one({"email": email}))


class AvaliacaoRepositoryMongo(AvaliacaoRepository):
    def __init__(self, db):
        self.col = db.avaliacoes

    def salvar(self, avaliacao: Avaliacao) -> Avaliacao:
        self.col.replace_one({"_id": avaliacao.id}, _para_doc(avaliacao), upsert=True)
        return avaliacao

    def obter(self, filme_id: str, usuario_id: str) -> Optional[Avaliacao]:
        return _de_doc(Avaliacao, self.col.find_one({"filme_id": filme_id, "usuario_id": usuario_id}))

    def listar_por_filme(self, filme_id: str) -> List[Avaliacao]:
        return [_de_doc(Avaliacao, d) for d in self.col.find({"filme_id": filme_id}).sort("criada_em", -1)]


class AnuncioRepositoryMongo(AnuncioRepository):
    def __init__(self, db):
        self.col = db.anuncios

    def salvar(self, anuncio: Anuncio) -> Anuncio:
        self.col.replace_one({"_id": anuncio.id}, _para_doc(anuncio), upsert=True)
        return anuncio

    def listar_ativos(self) -> List[Anuncio]:
        return [_de_doc(Anuncio, d) for d in self.col.find({"ativo": True})]


class IngressoRepositoryMongo(IngressoRepository):
    def __init__(self, db):
        self.col = db.ingressos

    def salvar(self, ingresso: Ingresso) -> Ingresso:
        self.col.replace_one({"_id": ingresso.id}, _para_doc(ingresso), upsert=True)
        return ingresso

    def listar_por_usuario(self, usuario_id: str) -> List[Ingresso]:
        return [_de_doc(Ingresso, d) for d in self.col.find({"usuario_id": usuario_id}).sort("comprado_em", -1)]
