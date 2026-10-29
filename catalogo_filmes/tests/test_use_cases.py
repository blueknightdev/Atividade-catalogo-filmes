"""Testes dos casos de uso, usando só adapters em memória (sem Django, Mongo ou rede)."""
import unittest

from core import use_cases as uc
from core.entities import Filme
from core.exceptions import (
    DadosInvalidos,
    IdadeInsuficiente,
    JaExiste,
    NaoAutenticado,
    NaoAutorizado,
)
from core.ports import ArmazenamentoArquivos, CatalogoExterno
from interfaces import memory_repositories as mem
from interfaces.security import HashSenhaPBKDF2, TokenHMAC


class CatalogoFalso(CatalogoExterno):
    def buscar_filme(self, tmdb_id):
        return {"nome": "Filme TMDB", "duracao": 120, "categorias": ["Ação"], "idade": 14,
                "sinopse": "x", "poster_url": "http://img/p.jpg"}


class ArquivosFalso(ArmazenamentoArquivos):
    def salvar_url_remota(self, url, chave):
        return f"https://s3.fake/{chave}"

    def salvar_bytes(self, dados, chave, content_type):
        return f"https://s3.fake/{chave}"


class Base(unittest.TestCase):
    def setUp(self):
        self.filmes = mem.FilmeRepositoryMemoria()
        self.usuarios = mem.UsuarioRepositoryMemoria()
        self.avaliacoes = mem.AvaliacaoRepositoryMemoria()
        self.ingressos = mem.IngressoRepositoryMemoria()
        self.anuncios = mem.AnuncioRepositoryMemoria()
        self.hasher = HashSenhaPBKDF2()
        self.tokens = TokenHMAC("segredo")
        cadastrar = uc.CadastrarUsuario(self.usuarios, self.hasher)
        self.admin = cadastrar.executar("Admin", "admin@x.com", "senha123", 30, is_admin=True)
        self.adulto = cadastrar.executar("Ana", "ana@x.com", "senha123", 25)
        self.crianca = cadastrar.executar("Davi", "davi@x.com", "senha123", 10)

    def novo_filme(self, **kw):
        base = dict(nome="Matrix", duracao=136, idade=14, categorias=["Ficção", "Ação"])
        base.update(kw)
        return uc.CadastrarFilme(self.filmes).executar(self.admin, **base)


class TestEntidades(unittest.TestCase):
    def test_classificacao_derivada_da_idade(self):
        self.assertEqual(Filme(nome="A", duracao=90, idade=0).classificacao, "L")
        self.assertEqual(Filme(nome="A", duracao=90, idade=14).classificacao, "14")
        self.assertEqual(Filme(nome="A", duracao=90, idade=17).classificacao, "18")

    def test_validacoes(self):
        with self.assertRaises(DadosInvalidos):
            Filme(nome=" ", duracao=90)
        with self.assertRaises(DadosInvalidos):
            Filme(nome="A", duracao=0)


class TestUsuarios(Base):
    def test_email_duplicado(self):
        with self.assertRaises(JaExiste):
            uc.CadastrarUsuario(self.usuarios, self.hasher).executar("Ana 2", "ANA@x.com", "senha123", 20)

    def test_login_ok_e_token(self):
        token, usuario = uc.Login(self.usuarios, self.hasher, self.tokens).executar("ana@x.com", "senha123")
        atual = uc.ObterUsuarioAutenticado(self.usuarios, self.tokens).executar(token)
        self.assertEqual(atual.id, usuario.id)

    def test_login_senha_errada(self):
        with self.assertRaises(NaoAutenticado):
            uc.Login(self.usuarios, self.hasher, self.tokens).executar("ana@x.com", "errada")

    def test_token_adulterado(self):
        with self.assertRaises(NaoAutenticado):
            uc.ObterUsuarioAutenticado(self.usuarios, self.tokens).executar("lixo")


class TestFilmes(Base):
    def test_so_admin_cadastra(self):
        with self.assertRaises(NaoAutorizado):
            uc.CadastrarFilme(self.filmes).executar(self.adulto, nome="X", duracao=90)

    def test_importar_tmdb(self):
        filme = uc.ImportarFilmeDoTMDB(self.filmes, CatalogoFalso(), ArquivosFalso()).executar(self.admin, 603)
        self.assertEqual(filme.poster_url, "https://s3.fake/posters/tmdb-603.jpg")
        self.assertEqual(filme.categorias, ["ação"])
        with self.assertRaises(JaExiste):
            uc.ImportarFilmeDoTMDB(self.filmes, CatalogoFalso(), ArquivosFalso()).executar(self.admin, 603)

    def test_listar_e_filtrar(self):
        self.novo_filme()
        self.novo_filme(nome="Toy Story", duracao=81, idade=0, categorias=["Animação"])
        self.assertEqual(len(uc.ListarFilmes(self.filmes).executar()), 2)
        f = uc.FiltrarFilmes(self.filmes)
        self.assertEqual([x.nome for x in f.executar(categoria="Animação")], ["Toy Story"])
        self.assertEqual([x.nome for x in f.executar(idade_max=10)], ["Toy Story"])
        self.assertEqual([x.nome for x in f.executar(nome="matr")], ["Matrix"])
        self.assertEqual([x.nome for x in f.executar(duracao_max=100)], ["Toy Story"])


class TestAvaliacao(Base):
    def test_media_e_edicao(self):
        filme = self.novo_filme()
        avaliar = uc.AvaliarFilme(self.filmes, self.avaliacoes)
        avaliar.executar(self.adulto, filme.id, 8)
        avaliar.executar(self.crianca, filme.id, 6)
        self.assertEqual(self.filmes.obter(filme.id).avaliacao, 7.0)
        avaliar.executar(self.adulto, filme.id, 10)  # edita a nota existente
        atual = self.filmes.obter(filme.id)
        self.assertEqual(atual.avaliacao, 8.0)
        self.assertEqual(atual.total_avaliacoes, 2)

    def test_nota_invalida(self):
        filme = self.novo_filme()
        with self.assertRaises(DadosInvalidos):
            uc.AvaliarFilme(self.filmes, self.avaliacoes).executar(self.adulto, filme.id, 11)


class TestIngressos(Base):
    def test_compra(self):
        filme = self.novo_filme()
        ing = uc.ComprarIngresso(self.filmes, self.ingressos, 30).executar(self.adulto, filme.id, 2)
        self.assertEqual(ing.valor_total, 60.0)

    def test_bloqueia_menor_de_idade(self):
        filme = self.novo_filme()
        with self.assertRaises(IdadeInsuficiente):
            uc.ComprarIngresso(self.filmes, self.ingressos).executar(self.crianca, filme.id, 1)


class TestAnuncios(Base):
    def test_criar_e_listar(self):
        filme = self.novo_filme()
        uc.CriarAnuncio(self.anuncios, self.filmes).executar(self.admin, "Estreia!", filme_id=filme.id)
        self.assertEqual(len(uc.ListarAnuncios(self.anuncios).executar()), 1)
        with self.assertRaises(NaoAutorizado):
            uc.CriarAnuncio(self.anuncios, self.filmes).executar(self.adulto, "Hack")


if __name__ == "__main__":
    unittest.main()
