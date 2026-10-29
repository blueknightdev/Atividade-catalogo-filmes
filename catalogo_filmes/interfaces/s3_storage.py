"""Adapters de armazenamento de arquivos: Amazon S3 (boto3) e disco local (dev)."""
from __future__ import annotations

import os
import urllib.request

from core.ports import ArmazenamentoArquivos


class S3Storage(ArmazenamentoArquivos):
    def __init__(self, bucket: str, regiao: str = "us-east-1", url_base: str = ""):
        import boto3  # import tardio

        self.bucket = bucket
        self.url_base = url_base or f"https://{bucket}.s3.{regiao}.amazonaws.com"
        self.client = boto3.client("s3", region_name=regiao)

    def salvar_bytes(self, dados: bytes, chave: str, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(Bucket=self.bucket, Key=chave, Body=dados, ContentType=content_type)
        return f"{self.url_base}/{chave}"

    def salvar_url_remota(self, url: str, chave: str) -> str:
        with urllib.request.urlopen(url, timeout=15) as resp:
            dados = resp.read()
            tipo = resp.headers.get_content_type()
        return self.salvar_bytes(dados, chave, tipo)


class ArmazenamentoLocal(ArmazenamentoArquivos):
    """Fallback para desenvolvimento sem credenciais AWS."""

    def __init__(self, pasta: str = "media", url_base: str = "/media"):
        self.pasta = pasta
        self.url_base = url_base.rstrip("/")

    def salvar_bytes(self, dados: bytes, chave: str, content_type: str = "") -> str:
        caminho = os.path.join(self.pasta, chave)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "wb") as f:
            f.write(dados)
        return f"{self.url_base}/{chave}"

    def salvar_url_remota(self, url: str, chave: str) -> str:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return self.salvar_bytes(resp.read(), chave)
