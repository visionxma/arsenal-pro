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

> ⚠️ **INVARIANTE — NÃO REMOVER (sincronização de experts):** apagar/editar/adicionar
> um expert em **qualquer** Painel Admin deve refletir **em todos os painéis abertos e
> na roleta**, e o expert removido **não pode voltar** ao recarregar nenhuma tela —
> com **qualquer número de máquinas no mesmo login**, inclusive uma que estava offline.
>
> Isso depende de:
> 1. **Relógio lógico (Lamport)**, não `Date.now()`. `tick()` faz
>    `relogio = max(relogio, revRecebido) + 1`. Usar relógio de parede fazia a máquina
>    com o relógio adiantado (ou simplesmente a que editou por último) sobrescrever o
>    trabalho da outra.
> 2. **Mesclagem, nunca substituição.** `mesclarExperts()` une por id; para cada id
>    vence o maior `updatedAt`. É comutativa: a ordem de chegada não importa.
> 3. **Lápides** (`cj_experts_tumbas_v1`): remover grava `tumbas[id] = tick()`. Sem
>    isso, uma máquina desatualizada ressuscitava quem já tinha sido excluído.
>    A lápide só mata se for mais nova que o `updatedAt` do expert — assim um
>    recadastro proposital depois da exclusão continua valendo.
> 4. Canal com `broadcast:{self:false}` e `dedupeExperts` (por id **e** nome) nos dois.
> 5. **Painel sem lista nasce vazio** e pede a lista (`reqExperts`) antes de publicar
>    qualquer coisa (`sendState()` retorna `false` enquanto `listaPropria` for falso).
>    Semear os 16 padrão de cara e mesclar depois ressuscitava os excluídos.
>    Se ninguém responder, o painel **pergunta ao operador** — nunca semeia sozinho.
> 6. A roleta guarda o maior relógio já visto (`cj_rev_visto_v1`) e o entrega ao painel
>    recém-aberto. Sem esse número o painel novo começaria do zero e **toda edição dele
>    perderia** para as outras máquinas.
>
> ⚠️ **INVARIANTE — SORTEIO:** enquanto a rodada não reiniciar, a roleta **nunca** pode
> parar em quem já foi sorteado. Isso inclui o "forçar próximo sorteado", que é
> procurado no **pool disponível** (não em `activeExperts()`), e o fallback por índice
> em `acabouGiro`, que só aceita quem ainda não saiu. O select do painel não oferece
> quem já foi sorteado. Quando todos passam, um novo ciclo reabre a rodada.
>
> Ao mexer, testar com **2 painéis + 1 roleta** conectados: remover em um reflete nos
> outros e não volta ao recarregar; e uma rodada completa não pode repetir ninguém.
> A tela da roleta atualiza sozinha (auto-refresh via `roleta/version.json`, só quando
> ociosa — nunca no meio de um sorteio), então **bump `version.json` ao alterar
> `roleta/index.html`**.
>
> Ambiente de teste isolado e suíte Playwright: `testes-roleta/` (ver README de lá).

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

As LPs por expert são cópias da landing; as diferenças são a const `CHECKOUT_URL`
(link do produto de cada expert na PerfectPay), o selo "Indicado por" no hero
(foto em `../assets/experts/…`, um nível abaixo da raiz) e o `<title>`/`og:title`
com o nome do expert. As páginas não têm rodapé (removido junto com a marca visível).

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
