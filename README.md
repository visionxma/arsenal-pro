# Arsenal Pro · Night Challenge Safirion

Landing page de vendas do Arsenal Pro e sistema do Corujão de Traders, com a identidade visual da Safirion.

## Rotas

| Rota | Descrição | Identidade |
|---|---|---|
| `/` | Landing page de vendas do Arsenal Pro | Safirion (navy + azul elétrico) |
| `/corujao` | Página convite do Corujão de Traders (live); CTA vai para o Google Meet do evento | Corujão (preto #0a0a0a + #00A7FF, assets reais do evento) |
| `/roleta` | Roleta de sorteio de experts (visual "roleta premiada": aro com luzes, sons, confete) com cronômetro e painel admin | Corujão |

## Roleta de Experts

- Sorteio aleatório com animação de giro; o expert sorteado sai da roleta até todos passarem pela rodada (rodízio).
- Cronômetro automático com tempo configurável no Painel Admin.
- Painel Admin: adicionar, editar, remover, ativar/desativar experts (nome + foto) e configurar o tempo padrão.
- Acesso ao Painel Admin protegido por tela de login. Senha padrão: `corujao2026` (troque a constante `ADMIN_PASS` em `roleta/index.html`). Proteção client-side, adequada para uso durante o evento.
- Dados persistidos em `localStorage`; sincronização em tempo real entre painel e roleta via Supabase Realtime.

## Configuração antes de usar

- `index.html`: constante `CHECKOUT_URL` (link de checkout do Arsenal Pro).
- `corujao/index.html`: constante `GROUP_URL` (link do Google Meet do evento).
- Fotos reais dos traders na seção de prova social do `index.html`.

Site estático, sem build. Para rodar localmente: `python -m http.server` na raiz.
