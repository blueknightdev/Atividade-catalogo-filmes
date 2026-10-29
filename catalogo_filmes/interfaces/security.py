"""Hash de senha (PBKDF2) e tokens assinados (HMAC), só com a biblioteca padrão."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Optional

from core.ports import HashSenha, TokenService


class HashSenhaPBKDF2(HashSenha):
    ITERACOES = 200_000

    def gerar(self, senha: str) -> str:
        sal = secrets.token_hex(16)
        h = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), self.ITERACOES).hex()
        return f"pbkdf2_sha256${self.ITERACOES}${sal}${h}"

    def verificar(self, senha: str, hash_: str) -> bool:
        try:
            _, iteracoes, sal, esperado = hash_.split("$")
            h = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), int(iteracoes)).hex()
            return hmac.compare_digest(h, esperado)
        except (ValueError, TypeError):
            return False


class TokenHMAC(TokenService):
    def __init__(self, segredo: str, validade_segundos: int = 60 * 60 * 24):
        self.segredo = segredo.encode()
        self.validade = validade_segundos

    def _assinar(self, payload: str) -> str:
        return hmac.new(self.segredo, payload.encode(), hashlib.sha256).hexdigest()

    def emitir(self, usuario_id: str) -> str:
        expira = int(time.time()) + self.validade
        payload = f"{usuario_id}.{expira}"
        bruto = f"{payload}.{self._assinar(payload)}"
        return base64.urlsafe_b64encode(bruto.encode()).decode()

    def validar(self, token: str) -> Optional[str]:
        try:
            bruto = base64.urlsafe_b64decode(token.encode()).decode()
            usuario_id, expira, assinatura = bruto.split(".")
            if not hmac.compare_digest(self._assinar(f"{usuario_id}.{expira}"), assinatura):
                return None
            if int(expira) < time.time():
                return None
            return usuario_id
        except Exception:
            return None
