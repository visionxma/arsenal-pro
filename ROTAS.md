# Rotas do Arsenal Pro

Domínio: **safiriontradingbrasil.com** (zona no Cloudflare). O site continua hospedado no
GitHub Pages (`visionxma.github.io/arsenal-pro/`) e entra no domínio como rotas:

- Público (sufixo): `safiriontradingbrasil.com/arsenal-pro/…`
- Painel admin (prefixo): `admin.safiriontradingbrasil.com`

O proxy fica em `infra/proxy-worker/` (Cloudflare Worker — publicar NA CONTA que possui a
zona): `cd infra/proxy-worker && npx wrangler login && npx wrangler deploy`. Único registro
DNS novo: `AAAA admin → 100::` com proxy (nuvem laranja). Nenhum registro existente muda.

A comunicação painel ↔ roleta usa **Supabase Realtime** (chave anon no código) e funciona
de qualquer dispositivo/navegador — não depende mais de mesma origem.
Todas as páginas são estáticas (`index.html` por pasta) e **todos os links internos são
relativos** — o site funciona igual na raiz de um domínio, em um subdiretório ou no
GitHub Pages, sem nenhuma configuração de servidor.

## Rotas públicas

| Rota | Arquivo | O que é |
|---|---|---|
| `/` | `index.html` | Landing page do Arsenal Pro (oferta R$ 997) — checkout genérico na const `CHECKOUT_URL` |
| `/julin/` | `julin/index.html` | LP do Arsenal Pro do Julin trader (checkout PerfectPay próprio) |
| `/eduardo/` | `eduardo/index.html` | LP do Arsenal Pro do Eduardo Bastos (checkout PerfectPay próprio) |
| `/thon/` | `thon/index.html` | LP do Arsenal Pro do Thon trader (checkout PerfectPay próprio) |
| `/vitao/` | `vitao/index.html` | LP do Arsenal Pro do Vitão trader (checkout PerfectPay próprio) |
| `/edlaine/` | `edlaine/index.html` | LP do Arsenal Pro da Edlaine trader (checkout PerfectPay próprio) |
| `/corujao/` | `corujao/index.html` | Pré-página do Corujão de Traders (pôster do evento); CTA vai para o Google Meet do evento |
| `/roleta/` | `roleta/index.html` | Roleta dos Experts (pública, exibida na live) |

As LPs por expert são cópias idênticas da landing; a única diferença é a const
`CHECKOUT_URL` (link do produto de cada expert na PerfectPay). O logo do rodapé
usa `../assets/logo.svg` por estarem um nível abaixo da raiz.

## Rotas restritas (operador)

| Rota | Arquivo | O que é |
|---|---|---|
| `/roleta/admin/` | `roleta/admin/index.html` | Painel Admin da roleta (senha no arquivo, const `ADMIN_PASS`) |

## Extras

| Rota | Arquivo | O que é |
|---|---|---|
| `404` | `404.html` | Página de erro; redireciona para `/` em 6s (usada automaticamente por GitHub Pages, Netlify, Vercel e Cloudflare Pages) |
| — | `assets/` | Logo e imagens compartilhadas |

## Ligações entre as páginas

- `/corujao/` → Google Meet do evento (CTA "Clique aqui e entre agora!", const `GROUP_URL`)
- `/roleta/` → `/` (link "← Arsenal Pro") e `/roleta/admin/` (link "Painel Admin", nova aba)
- `/roleta/admin/` → `/roleta/` (item "Abrir a roleta", nova aba)
- `/` não tem navegação de saída (landing fechada na copy oficial; o checkout é a const `CHECKOUT_URL` no `index.html`)

## Pendências antes de publicar

- `index.html` → `CHECKOUT_URL` (link real do checkout)
- `roleta/index.html` e `roleta/admin/index.html` → `ADMIN_PASS` (trocar a senha; manter a MESMA nos dois arquivos)

## Observações de hospedagem

- **Painel × Roleta**: comunicam por `localStorage` + `BroadcastChannel` → precisam do
  **mesmo domínio e mesmo navegador** (abas/janelas do operador). Servidos como rotas do
  mesmo domínio, isso já está garantido.
- Não há rewrites nem rotas dinâmicas: qualquer host estático serve o site como está.
- Se o host oferecer "clean URLs", nada muda — as rotas já são pastas com `index.html`.
