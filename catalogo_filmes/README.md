# Catálogo de Filmes — Clean Architecture

Implementação do diagrama: as dependências apontam sempre para dentro
(`frameworks` → `interfaces` → `core`). O `core` não importa Django, MongoDB, TMDB nem S3.

| Camada do diagrama | Pasta | Conteúdo |
|---|---|---|
| **Entidade** | `core/entities.py` | `Filme` (id, nome, categorias, duração, idade, classificação, avaliação), `Usuario`, `Avaliacao`, `Anuncio`, `Ingresso` |
| **Caso de uso** | `core/use_cases.py` | Cadastrar filme, Anúncios, Venda de ingressos, Filtrar filmes, Listar filmes, Avaliar filme, Login e cadastro |
| (portas) | `core/ports.py` | Interfaces abstratas que os casos de uso exigem |
| **Interface** | `interfaces/` | Adapters: `tmdb_client.py` (TMDB), `mongo_repositories.py` (MongoDB), `s3_storage.py` (Amazon S3), `memory_repositories.py`, `security.py` |
| **Frameworks e drivers** | `frameworks/django_app/` | Django (settings, urls, views JSON) e `container.py`, que monta tudo |

## Rodando

```bash
pip install -r requirements.txt
python manage.py runserver
```

Por padrão usa repositórios **em memória** e armazenamento **local**, então roda sem
MongoDB nem AWS. Variáveis de ambiente:

| Variável | Valor | Efeito |
|---|---|---|
| `DB_BACKEND` | `mongo` | Usa MongoDB (`MONGO_URI`, `MONGO_DB`) |
| `STORAGE_BACKEND` | `s3` | Guarda pôsteres no S3 (`S3_BUCKET`, `AWS_REGION`, credenciais AWS padrão) |
| `TMDB_API_KEY` | chave | Habilita a importação de filmes do TMDB |
| `ADMIN_EMAILS` | `a@x.com,b@x.com` | E-mails que viram administradores ao se cadastrar |
| `SECRET_KEY` | texto | Assina os tokens de login (**troque em produção**) |
| `PRECO_INGRESSO` | `30.0` | Preço unitário do ingresso |
| `SEED_DEMO` | `0` | Desativa os dados de demonstração (modo em memória) |

## Front end

Página única em HTML/CSS/JS puro (`frontend/`), servida pelo próprio Django. Depois de
`python manage.py runserver`, abra <http://localhost:8000/>.

| Requisito do diagrama | No front end |
|---|---|
| Listar filmes | Grade de cartões (pôster, nome, duração, classificação, nota, categorias) com "Carregar mais" |
| Filtrar filmes | Barra de filtros: nome, categoria, classificação, idade máx., duração máx., nota mín. |
| Login e cadastro | Janela com abas Entrar / Cadastrar; sessão guardada no navegador |
| Avaliar filme | Nota de 0 a 10 + comentário no detalhe do filme; a média é atualizada na grade |
| Venda de ingressos | Compra no detalhe do filme (avisa se a idade for insuficiente) e janela "Meus ingressos" |
| Anúncios | Faixa rotativa no topo; clicar abre o link ou o filme relacionado |
| Cadastrar filme | "Painel admin": cadastro manual, importação do TMDB (pôster vai para o S3) e novo anúncio |

No modo em memória (padrão) o servidor sobe com **dados de demonstração** (`SEED_DEMO=0` desativa):

| Conta | E-mail | Senha |
|---|---|---|
| Administrador | `admin@demo.com` | `admin123` |
| Usuária de 17 anos | `ana@demo.com` | `demo123` |
| Usuário de 25 anos | `davi@demo.com` | `demo123` |

Os dados somem ao reiniciar; com `DB_BACKEND=mongo` nada é semeado.

## Endpoints

| Método | Rota | Caso de uso | Auth |
|---|---|---|---|
| POST | `/api/cadastro/` | Cadastro | — |
| POST | `/api/login/` | Login (devolve `token`) | — |
| GET | `/api/filmes/` | Listar; com `nome`, `categoria`, `classificacao`, `idade_max`, `duracao_max`, `nota_min`, `limite`, `offset` vira Filtrar | — |
| POST | `/api/filmes/` | Cadastrar filme | admin |
| POST | `/api/filmes/importar-tmdb/` | Importar do TMDB (`{"tmdb_id": 603}`) | admin |
| GET | `/api/filmes/<id>/` | Detalhe | — |
| GET/POST | `/api/filmes/<id>/avaliacoes/` | Listar / avaliar (`nota` 0–10) | POST exige login |
| GET/POST | `/api/ingressos/` | Meus ingressos / comprar (`filme_id`, `quantidade`) | login |
| GET/POST | `/api/anuncios/` | Listar / criar | POST admin |

Autenticação: header `Authorization: Bearer <token>`.

```bash
curl -X POST localhost:8000/api/cadastro/ -H 'Content-Type: application/json' \
  -d '{"nome":"Ana","email":"ana@x.com","senha":"senha123","idade":25}'
```

## Testes

```bash
python -m unittest discover -s tests -t . -v
```

`tests/test_use_cases.py` não precisa de Django (só adapters em memória);
`tests/test_api.py` exercita a API completa e precisa do Django instalado.

## Regras de negócio implementadas

- Classificação derivada da idade mínima (L, 10, 12, 14, 16, 18) quando não informada.
- Média de avaliação recalculada de forma incremental; reavaliar edita a nota do usuário.
- Venda de ingressos bloqueada se a idade do usuário for menor que a do filme.
- Importar do TMDB copia o pôster para o S3; se o S3 falhar, mantém a URL do TMDB.
