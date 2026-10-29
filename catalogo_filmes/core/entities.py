"""Camada 1 — ENTIDADES.

Regras de negócio puras. Aqui não existe Django, MongoDB, HTTP ou S3.
Campos de Filme seguem o diagrama: ID, NOME, CATEGORIAS, DURAÇÃO, IDADE,
CLASSIFICAÇÃO e AVALIAÇÃO.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from .exceptions import DadosInvalidos

CLASSIFICACOES = ("L", "10", "12", "14", "16", "18")


def novo_id() -> str:
    return uuid.uuid4().hex


def agora() -> datetime:
    return datetime.now(timezone.utc)


def classificacao_por_idade(idade: int) -> str:
    """Converte a idade mínima na classificação indicativa brasileira."""
    if idade <= 0:
        return "L"
    for faixa in (10, 12, 14, 16):
        if idade <= faixa:
            return str(faixa)
    return "18"


@dataclass
class Filme:
    nome: str
    duracao: int  # minutos
    idade: int = 0  # idade mínima recomendada
    categorias: List[str] = field(default_factory=list)
    classificacao: str = ""
    avaliacao: float = 0.0  # média das notas (0 a 10)
    total_avaliacoes: int = 0
    id: str = field(default_factory=novo_id)
    tmdb_id: Optional[int] = None
    sinopse: str = ""
    poster_url: str = ""

    def __post_init__(self):
        self.nome = (self.nome or "").strip()
        if not self.nome:
            raise DadosInvalidos("O nome do filme é obrigatório.")
        if self.duracao is None or int(self.duracao) <= 0:
            raise DadosInvalidos("A duração deve ser maior que zero (em minutos).")
        self.duracao = int(self.duracao)
        if int(self.idade) < 0:
            raise DadosInvalidos("A idade não pode ser negativa.")
        self.idade = int(self.idade)
        self.categorias = sorted({c.strip().lower() for c in self.categorias if c and c.strip()})
        if not self.classificacao:
            self.classificacao = classificacao_por_idade(self.idade)
        if self.classificacao not in CLASSIFICACOES:
            raise DadosInvalidos(f"Classificação inválida. Use uma de: {', '.join(CLASSIFICACOES)}.")

    def registrar_nota(self, nota: float, nota_anterior: Optional[float] = None) -> None:
        """Atualiza a média incrementalmente (nova nota ou edição de uma nota existente)."""
        soma = self.avaliacao * self.total_avaliacoes
        if nota_anterior is None:
            self.total_avaliacoes += 1
            soma += nota
        else:
            soma += nota - nota_anterior
        self.avaliacao = round(soma / self.total_avaliacoes, 2)

    def permitido_para(self, idade_usuario: int) -> bool:
        return idade_usuario >= self.idade


@dataclass
class Usuario:
    nome: str
    email: str
    senha_hash: str
    idade: int
    is_admin: bool = False
    id: str = field(default_factory=novo_id)

    def __post_init__(self):
        self.nome = (self.nome or "").strip()
        self.email = (self.email or "").strip().lower()
        if not self.nome:
            raise DadosInvalidos("O nome é obrigatório.")
        if "@" not in self.email or "." not in self.email.split("@")[-1]:
            raise DadosInvalidos("E-mail inválido.")
        if int(self.idade) < 0 or int(self.idade) > 130:
            raise DadosInvalidos("Idade inválida.")
        self.idade = int(self.idade)


@dataclass
class Avaliacao:
    filme_id: str
    usuario_id: str
    nota: float
    comentario: str = ""
    id: str = field(default_factory=novo_id)
    criada_em: datetime = field(default_factory=agora)

    def __post_init__(self):
        try:
            self.nota = float(self.nota)
        except (TypeError, ValueError):
            raise DadosInvalidos("A nota deve ser numérica.")
        if not 0 <= self.nota <= 10:
            raise DadosInvalidos("A nota deve estar entre 0 e 10.")


@dataclass
class Anuncio:
    titulo: str
    imagem_url: str = ""
    link: str = ""
    filme_id: Optional[str] = None
    ativo: bool = True
    id: str = field(default_factory=novo_id)

    def __post_init__(self):
        self.titulo = (self.titulo or "").strip()
        if not self.titulo:
            raise DadosInvalidos("O título do anúncio é obrigatório.")


@dataclass
class Ingresso:
    filme_id: str
    usuario_id: str
    quantidade: int
    valor_total: float
    id: str = field(default_factory=novo_id)
    comprado_em: datetime = field(default_factory=agora)

    def __post_init__(self):
        if int(self.quantidade) <= 0:
            raise DadosInvalidos("A quantidade de ingressos deve ser maior que zero.")
        self.quantidade = int(self.quantidade)
