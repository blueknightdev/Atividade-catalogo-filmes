"use strict";

/* =========================================================================
   CineCatálogo — front end (HTML/CSS/JS puro) que consome a API Django.
   Todo texto vindo da API é inserido com textContent (nunca innerHTML).
   ========================================================================= */

const API = "/api";
const POR_PAGINA = 12;

const $ = (sel, raiz = document) => raiz.querySelector(sel);
const $$ = (sel, raiz = document) => [...raiz.querySelectorAll(sel)];

const state = {
  token: localStorage.getItem("token"),
  user: lerJSON(localStorage.getItem("user")),
  offset: 0,
  requisicao: 0,
  categorias: new Set(),
  anuncios: [],
  anuncioAtual: 0,
};

function lerJSON(texto) {
  try { return JSON.parse(texto); } catch { return null; }
}

/* ------------------------------ utilidades ------------------------------ */
function h(tag, props = {}, ...filhos) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const f of filhos.flat()) {
    if (f != null && f !== false) el.append(f.nodeType ? f : document.createTextNode(f));
  }
  return el;
}

function urlSegura(u) {
  if (!u) return "";
  try {
    const x = new URL(u, location.origin);
    return ["http:", "https:"].includes(x.protocol) ? u : "";
  } catch { return ""; }
}

const moeda = (v) => Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const dataHora = (iso) => new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });

function duracao(min) {
  const hh = Math.floor(min / 60), mm = min % 60;
  return hh ? `${hh}h${String(mm).padStart(2, "0")}` : `${mm}min`;
}

function toast(msg, erro = false) {
  const t = h("div", { class: "toast" + (erro ? " erro" : ""), text: msg });
  $("#toasts").append(t);
  setTimeout(() => t.remove(), erro ? 5000 : 3000);
}

async function api(caminho, { method = "GET", body } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  const resp = await fetch(API + caminho, {
    method, headers, body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  let dados = null;
  try { dados = await resp.json(); } catch { /* resposta sem corpo */ }
  if (!resp.ok) {
    if (resp.status === 401 && state.token) {
      sair(false);
      throw new Error("Sua sessão expirou. Entre novamente.");
    }
    throw new Error((dados && dados.erro) || `Erro ${resp.status}`);
  }
  return dados;
}

/** Executa uma ação assíncrona mostrando erros como aviso. */
async function seguro(fn) {
  try { return await fn(); } catch (e) { toast(e.message || "Algo deu errado.", true); }
}

/* ------------------------------ sessão / topo ---------------------------- */
function iniciarSessao(token, usuario) {
  state.token = token;
  state.user = usuario;
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(usuario));
  renderNav();
}

function sair(aviso = true) {
  state.token = null;
  state.user = null;
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  renderNav();
  if (aviso) toast("Você saiu da conta.");
}

function renderNav() {
  const nav = $("#nav");
  nav.replaceChildren();
  if (!state.user) {
    nav.append(
      h("button", { class: "btn ghost", onclick: () => abrirAuth("login") }, "Entrar"),
      h("button", { class: "btn primary", onclick: () => abrirAuth("cadastro") }, "Cadastrar"),
    );
    return;
  }
  nav.append(h("span", { class: "ola", text: `Olá, ${state.user.nome.split(" ")[0]}` }));
  if (state.user.is_admin) {
    nav.append(h("button", { class: "btn", onclick: abrirAdmin }, "Painel admin"));
  }
  nav.append(
    h("button", { class: "btn", onclick: abrirIngressos }, "Meus ingressos"),
    h("button", { class: "btn ghost", onclick: () => sair() }, "Sair"),
  );
}

/* --------------------------- diálogos genéricos -------------------------- */
$$("dialog").forEach((dlg) => {
  dlg.addEventListener("click", (e) => {
    if (e.target === dlg || e.target.closest("[data-close]")) dlg.close();
  });
});

function trocarAba(dlg, nome, prefixoForm) {
  $$(".aba", dlg).forEach((b) => b.classList.toggle("ativa", b.dataset.aba === nome));
  $$("form", dlg).forEach((f) => { f.hidden = f.id !== `${prefixoForm}-${nome}`; });
}

/* ------------------------- LOGIN E CADASTRO ------------------------------ */
function abrirAuth(aba = "login") {
  trocarAba($("#dlg-auth"), aba, "form");
  $("#dlg-auth").showModal();
}

$$("#dlg-auth .aba").forEach((b) => b.addEventListener("click", () => trocarAba($("#dlg-auth"), b.dataset.aba, "form")));

function dadosDoForm(form) {
  return Object.fromEntries(new FormData(form).entries());
}

$("#form-login").addEventListener("submit", (e) => {
  e.preventDefault();
  seguro(async () => {
    const d = dadosDoForm(e.target);
    const r = await api("/login/", { method: "POST", body: { email: d.email, senha: d.senha } });
    iniciarSessao(r.token, r.usuario);
    e.target.reset();
    $("#dlg-auth").close();
    toast(`Bem-vindo(a), ${r.usuario.nome}!`);
  });
});

$("#form-cadastro").addEventListener("submit", (e) => {
  e.preventDefault();
  seguro(async () => {
    const d = dadosDoForm(e.target);
    await api("/cadastro/", { method: "POST", body: { ...d, idade: Number(d.idade) } });
    // após cadastrar, já entra na conta
    const r = await api("/login/", { method: "POST", body: { email: d.email, senha: d.senha } });
    iniciarSessao(r.token, r.usuario);
    e.target.reset();
    $("#dlg-auth").close();
    toast("Conta criada! Você já está logado.");
  });
});

/* ----------------------- LISTAR E FILTRAR FILMES ------------------------- */
function filtrosAtuais() {
  const p = new URLSearchParams();
  const campos = {
    nome: $("#f-nome").value.trim(),
    categoria: $("#f-categoria").value.trim(),
    classificacao: $("#f-classificacao").value,
    idade_max: $("#f-idade").value,
    duracao_max: $("#f-duracao").value,
    nota_min: $("#f-nota").value,
  };
  for (const [k, v] of Object.entries(campos)) if (v !== "") p.set(k, v);
  return p;
}

async function carregarFilmes(zerar = true) {
  const minha = ++state.requisicao; // descarta respostas antigas
  if (zerar) {
    state.offset = 0;
    $("#grade").replaceChildren();
    $("#status-lista").textContent = "Carregando...";
  }
  const params = filtrosAtuais();
  const temFiltro = [...params.keys()].length > 0;
  params.set("limite", POR_PAGINA);
  params.set("offset", state.offset);

  try {
    const { resultados } = await api(`/filmes/?${params}`);
    if (minha !== state.requisicao) return;
    resultados.forEach((f) => {
      f.categorias.forEach((c) => state.categorias.add(c));
      $("#grade").append(cartao(f));
    });
    state.offset += resultados.length;
    $("#btn-mais").hidden = resultados.length < POR_PAGINA;
    atualizarCategorias();
    const total = $("#grade").children.length;
    $("#status-lista").textContent = total
      ? `${total} filme${total > 1 ? "s" : ""} exibido${total > 1 ? "s" : ""}${temFiltro ? " (filtrado)" : ""}`
      : temFiltro ? "Nenhum filme encontrado com esses filtros." : "Nenhum filme cadastrado ainda.";
  } catch (e) {
    if (minha === state.requisicao) $("#status-lista").textContent = "Não foi possível carregar os filmes: " + e.message;
  }
}

function atualizarCategorias() {
  const lista = $("#lista-categorias");
  lista.replaceChildren(...[...state.categorias].sort().map((c) => h("option", { value: c })));
}

function selo(classificacao) {
  return h("span", { class: `class class-${classificacao}`, title: `Classificação: ${classificacao === "L" ? "livre" : classificacao + " anos"}`, text: classificacao });
}

function posterEl(f, comSelo = true) {
  const url = urlSegura(f.poster_url);
  return h("div", { class: "poster" },
    url ? h("img", { src: url, alt: `Pôster de ${f.nome}`, loading: "lazy" }) : h("span", { "aria-hidden": "true", text: f.nome.charAt(0).toUpperCase() }),
    comSelo ? h("span", { class: "badge-class" }, selo(f.classificacao)) : null,
  );
}

function notaEl(f) {
  return f.total_avaliacoes
    ? h("span", { class: "nota", title: `${f.total_avaliacoes} avaliação(ões)`, text: `★ ${f.avaliacao.toFixed(1)}` })
    : h("span", { class: "nota vazia", text: "Sem notas" });
}

function cartao(f) {
  return h("button", { class: "card", type: "button", onclick: () => abrirFilme(f.id) },
    posterEl(f),
    h("div", { class: "card-corpo" },
      h("div", { class: "card-titulo", text: f.nome }),
      h("div", { class: "meta" }, h("span", { text: duracao(f.duracao) }), notaEl(f)),
      h("div", { class: "chips" }, f.categorias.slice(0, 3).map((c) => h("span", { class: "chip", text: c }))),
    ),
  );
}

let temporizador;
$("#form-filtros").addEventListener("input", () => {
  clearTimeout(temporizador);
  temporizador = setTimeout(() => carregarFilmes(true), 300);
});
$("#form-filtros").addEventListener("submit", (e) => e.preventDefault());
$("#btn-limpar").addEventListener("click", () => {
  $("#form-filtros").reset();
  carregarFilmes(true);
});
$("#btn-mais").addEventListener("click", () => carregarFilmes(false));

/* ------------------------- DETALHE + AVALIAR + INGRESSOS ----------------- */
async function abrirFilme(id) {
  await seguro(async () => {
    const f = await api(`/filmes/${id}/`);
    const { resultados: avaliacoes } = await api(`/filmes/${id}/avaliacoes/`);
    renderFilme(f, avaliacoes);
    const dlg = $("#dlg-filme");
    if (!dlg.open) dlg.showModal();
  });
}

function renderFilme(f, avaliacoes) {
  const corpo = $("#corpo-filme");
  corpo.replaceChildren(
    h("div", { class: "detalhe" },
      posterEl(f, false),
      h("div", {},
        h("h2", { text: f.nome }),
        h("div", { class: "info" },
          selo(f.classificacao),
          h("span", { text: duracao(f.duracao) }),
          h("span", { text: f.idade ? `Idade mínima: ${f.idade} anos` : "Livre para todos" }),
          notaEl(f),
        ),
        h("div", { class: "chips" }, f.categorias.map((c) => h("span", { class: "chip", text: c }))),
        h("p", { class: "sinopse", text: f.sinopse || "Sem sinopse cadastrada." }),
        blocoIngresso(f),
        blocoAvaliar(f),
        blocoAvaliacoes(avaliacoes),
      ),
    ),
  );
}

/* --- VENDA DE INGRESSOS --- */
function blocoIngresso(f) {
  const bloco = h("div", { class: "bloco" }, h("h3", { text: "Comprar ingresso" }));
  if (!state.user) {
    bloco.append(h("button", { class: "btn primary", onclick: () => abrirAuth("login") }, "Entre para comprar"));
    return bloco;
  }
  if (state.user.idade < f.idade) {
    bloco.append(h("div", { class: "aviso", text: `Este filme exige ${f.idade} anos ou mais (classificação ${f.classificacao}). Sua idade cadastrada: ${state.user.idade}.` }));
    return bloco;
  }
  const qtd = h("input", { type: "number", min: "1", max: "10", value: "1", "aria-label": "Quantidade de ingressos" });
  const botao = h("button", { class: "btn primary", type: "button" }, "Comprar");
  botao.addEventListener("click", () => seguro(async () => {
    botao.disabled = true;
    try {
      const ing = await api("/ingressos/", { method: "POST", body: { filme_id: f.id, quantidade: Number(qtd.value) } });
      toast(`Compra confirmada: ${ing.quantidade} ingresso(s) — ${moeda(ing.valor_total)}`);
    } finally { botao.disabled = false; }
  }));
  bloco.append(h("div", { class: "linha" }, qtd, botao));
  return bloco;
}

/* --- AVALIAR FILME --- */
function blocoAvaliar(f) {
  const bloco = h("div", { class: "bloco" }, h("h3", { text: "Avaliar filme" }));
  if (!state.user) {
    bloco.append(h("button", { class: "btn", onclick: () => abrirAuth("login") }, "Entre para avaliar"));
    return bloco;
  }
  const saida = h("output", { text: "8.0" });
  const nota = h("input", { type: "range", min: "0", max: "10", step: "0.5", value: "8", "aria-label": "Nota de 0 a 10" });
  nota.addEventListener("input", () => { saida.textContent = Number(nota.value).toFixed(1); });
  const comentario = h("textarea", { rows: "2", placeholder: "Comentário (opcional)", maxlength: "500", "aria-label": "Comentário" });
  const form = h("form", { class: "form" },
    h("div", { class: "nota-range" }, nota, saida),
    comentario,
    h("button", { class: "btn", type: "submit" }, "Enviar avaliação"),
    h("p", { class: "dica", text: "Se você já avaliou este filme, a nota anterior será substituída." }),
  );
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    seguro(async () => {
      await api(`/filmes/${f.id}/avaliacoes/`, { method: "POST", body: { nota: Number(nota.value), comentario: comentario.value.trim() } });
      toast("Avaliação registrada!");
      await abrirFilme(f.id);
      carregarFilmes(true); // atualiza a média nos cartões
    });
  });
  bloco.append(form);
  return bloco;
}

function blocoAvaliacoes(lista) {
  const bloco = h("div", { class: "bloco" }, h("h3", { text: `Avaliações (${lista.length})` }));
  if (!lista.length) return (bloco.append(h("p", { class: "vazio", text: "Ainda não há avaliações." })), bloco);
  lista.forEach((a) => bloco.append(
    h("div", { class: "avaliacao" },
      h("span", { class: "nota", text: `★ ${Number(a.nota).toFixed(1)}` }), " ",
      h("small", { text: dataHora(a.criada_em) }),
      a.comentario ? h("div", { text: a.comentario }) : null,
    ),
  ));
  return bloco;
}

/* ---------------------------- MEUS INGRESSOS ----------------------------- */
async function abrirIngressos() {
  await seguro(async () => {
    const { resultados } = await api("/ingressos/");
    const corpo = $("#corpo-ingressos");
    corpo.replaceChildren();
    if (!resultados.length) {
      corpo.append(h("p", { class: "vazio", text: "Você ainda não comprou ingressos." }));
    } else {
      const ids = [...new Set(resultados.map((i) => i.filme_id))];
      const nomes = {};
      await Promise.all(ids.map(async (id) => {
        try { nomes[id] = (await api(`/filmes/${id}/`)).nome; } catch { nomes[id] = "Filme removido"; }
      }));
      resultados.forEach((i) => corpo.append(
        h("div", { class: "ingresso" },
          h("div", {}, h("strong", { text: nomes[i.filme_id] }), h("small", { text: dataHora(i.comprado_em) })),
          h("div", {}, `${i.quantidade}× — `, h("strong", { text: moeda(i.valor_total) })),
        ),
      ));
    }
    $("#dlg-ingressos").showModal();
  });
}

/* ------------------------------- ANÚNCIOS -------------------------------- */
async function carregarAnuncios() {
  try {
    state.anuncios = (await api("/anuncios/")).resultados;
  } catch { state.anuncios = []; }
  state.anuncioAtual = 0;
  renderAnuncio();
}

function renderAnuncio() {
  const caixa = $("#anuncios");
  caixa.replaceChildren();
  if (!state.anuncios.length) { caixa.hidden = true; return; }
  caixa.hidden = false;
  const a = state.anuncios[state.anuncioAtual % state.anuncios.length];
  const link = urlSegura(a.link);
  const img = urlSegura(a.imagem_url);
  const el = h("a", {
    class: "ad", href: link || "#", target: link ? "_blank" : null, rel: "noopener noreferrer",
    onclick: (e) => {
      if (!link) { e.preventDefault(); if (a.filme_id) abrirFilme(a.filme_id); }
    },
  },
    img ? h("img", { src: img, alt: "" }) : null,
    h("div", { class: "ad-text" }, h("span", { class: "tag", text: "Anúncio" }), h("strong", { text: a.titulo })),
  );
  caixa.append(el);
}

setInterval(() => {
  if (state.anuncios.length > 1 && !document.hidden) {
    state.anuncioAtual++;
    renderAnuncio();
  }
}, 6000);

/* ---------------------- PAINEL ADMIN: CADASTRAR FILME -------------------- */
async function abrirAdmin() {
  trocarAba($("#dlg-admin"), "filme", "form");
  // preenche o seletor de filmes do formulário de anúncio
  await seguro(async () => {
    const { resultados } = await api("/filmes/?limite=100");
    const sel = $("#form-anuncio [name=filme_id]");
    sel.replaceChildren(h("option", { value: "", text: "Nenhum" }), ...resultados.map((f) => h("option", { value: f.id, text: f.nome })));
  });
  $("#dlg-admin").showModal();
}

$$("#dlg-admin .aba").forEach((b) => b.addEventListener("click", () => trocarAba($("#dlg-admin"), b.dataset.aba, "form")));

$("#form-filme").addEventListener("submit", (e) => {
  e.preventDefault();
  seguro(async () => {
    const d = dadosDoForm(e.target);
    await api("/filmes/", {
      method: "POST",
      body: {
        nome: d.nome,
        duracao: Number(d.duracao),
        idade: Number(d.idade),
        classificacao: d.classificacao,
        categorias: d.categorias.split(",").map((c) => c.trim()).filter(Boolean),
        poster_url: d.poster_url,
        sinopse: d.sinopse,
      },
    });
    toast("Filme cadastrado!");
    e.target.reset();
    carregarFilmes(true);
  });
});

$("#form-tmdb").addEventListener("submit", (e) => {
  e.preventDefault();
  seguro(async () => {
    const f = await api("/filmes/importar-tmdb/", { method: "POST", body: { tmdb_id: Number(dadosDoForm(e.target).tmdb_id) } });
    toast(`"${f.nome}" importado do TMDB!`);
    e.target.reset();
    carregarFilmes(true);
  });
});

$("#form-anuncio").addEventListener("submit", (e) => {
  e.preventDefault();
  seguro(async () => {
    const d = dadosDoForm(e.target);
    await api("/anuncios/", {
      method: "POST",
      body: { titulo: d.titulo, imagem_url: d.imagem_url, link: d.link, filme_id: d.filme_id || null },
    });
    toast("Anúncio publicado!");
    e.target.reset();
    carregarAnuncios();
  });
});

/* -------------------------------- início --------------------------------- */
renderNav();
carregarAnuncios();
carregarFilmes(true);
