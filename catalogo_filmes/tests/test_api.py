"""Smoke test da API Django (backend em memória)."""
import os

os.environ["DJANGO_SETTINGS_MODULE"] = "frameworks.django_app.settings"
os.environ["ADMIN_EMAILS"] = "admin@x.com"
os.environ["DB_BACKEND"] = "memory"
os.environ["SEED_DEMO"] = "0"  # os testes partem de um catálogo vazio

import django

django.setup()

from django.test import SimpleTestCase  # noqa: E402

from frameworks.django_app.container import resetar_container  # noqa: E402


class TestAPI(SimpleTestCase):
    def setUp(self):
        resetar_container()

    def post(self, url, data, token=None):
        h = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return self.client.post(url, data, content_type="application/json", **h)

    def entrar(self, email, idade):
        self.post("/api/cadastro/", {"nome": "U", "email": email, "senha": "senha123", "idade": idade})
        return self.post("/api/login/", {"email": email, "senha": "senha123"}).json()["token"]

    def test_fluxo_completo(self):
        admin = self.entrar("admin@x.com", 30)
        user = self.entrar("ana@x.com", 16)

        # usuário comum não cadastra filme
        r = self.post("/api/filmes/", {"nome": "Matrix", "duracao": 136, "idade": 14, "categorias": ["Ação"]}, user)
        self.assertEqual(r.status_code, 403)

        r = self.post("/api/filmes/", {"nome": "Matrix", "duracao": 136, "idade": 14, "categorias": ["Ação"]}, admin)
        self.assertEqual(r.status_code, 201)
        filme_id = r.json()["id"]
        self.post("/api/filmes/", {"nome": "Pulp Fiction", "duracao": 154, "idade": 18, "categorias": ["Crime"]}, admin)

        self.assertEqual(len(self.client.get("/api/filmes/").json()["resultados"]), 2)
        self.assertEqual(len(self.client.get("/api/filmes/?categoria=ação").json()["resultados"]), 1)
        self.assertEqual(self.client.get(f"/api/filmes/{filme_id}/").json()["nome"], "Matrix")

        r = self.post(f"/api/filmes/{filme_id}/avaliacoes/", {"nota": 9, "comentario": "Ótimo"}, user)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.get(f"/api/filmes/{filme_id}/").json()["avaliacao"], 9.0)

        r = self.post("/api/ingressos/", {"filme_id": filme_id, "quantidade": 2}, user)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["valor_total"], 60.0)

        proibido = self.client.get("/api/filmes/?idade_max=18").json()["resultados"]
        pulp = next(f for f in proibido if f["nome"] == "Pulp Fiction")
        self.assertEqual(self.post("/api/ingressos/", {"filme_id": pulp["id"]}, user).status_code, 403)

        self.assertEqual(self.post("/api/anuncios/", {"titulo": "Estreia"}, admin).status_code, 201)
        self.assertEqual(len(self.client.get("/api/anuncios/").json()["resultados"]), 1)

    def test_sem_token(self):
        self.assertEqual(self.client.get("/api/ingressos/").status_code, 401)
        self.assertEqual(self.client.get("/api/filmes/nao-existe/").status_code, 404)
