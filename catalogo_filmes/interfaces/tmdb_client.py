"""Adapter do TMDB (The Movie Database), usando apenas a biblioteca padrão."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from core.exceptions import DadosInvalidos, NaoEncontrado
from core.ports import CatalogoExterno

BASE = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/w500"


class TMDBClient(CatalogoExterno):
    def __init__(self, api_key: str, idioma: str = "pt-BR", timeout: int = 10):
        if not api_key:
            raise DadosInvalidos("TMDB_API_KEY não configurada.")
        self.api_key = api_key
        self.idioma = idioma
        self.timeout = timeout

    def _get(self, caminho: str, **params) -> dict:
        params.update({"api_key": self.api_key, "language": self.idioma})
        url = f"{BASE}{caminho}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise NaoEncontrado("Filme não encontrado no TMDB.")
            raise

    def buscar_filme(self, tmdb_id: int) -> dict:
        d = self._get(f"/movie/{int(tmdb_id)}")
        return {
            "nome": d.get("title") or d.get("original_title", ""),
            "duracao": d.get("runtime") or 0,
            "categorias": [g["name"] for g in d.get("genres", [])],
            "idade": 18 if d.get("adult") else 0,
            "sinopse": d.get("overview", ""),
            "poster_url": f"{IMG_BASE}{d['poster_path']}" if d.get("poster_path") else "",
        }
