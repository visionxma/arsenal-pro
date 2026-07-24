# Arsenal Pro · Night Challenge Safirion

Landing page de vendas do Arsenal Pro e sistema do Corujão de Traders, com a identidade visual da Safirion.

## Rotas

| Rota | Descrição |
|---|---|
| `/` | Landing page de vendas do Arsenal Pro |
| `/corujao` | Página convite do Corujão de Traders (live) |
| `/aovivo` | Página da transmissão ao vivo + expert em operação |
| `/roleta` | Roleta de sorteio de experts com cronômetro e painel admin |

## Roleta de Experts

- Sorteio aleatório com animação de giro; o expert sorteado sai da roleta até todos passarem pela rodada (rodízio).
- Cronômetro automático com tempo configurável no Painel Admin.
- Painel Admin: adicionar, editar, remover, ativar/desativar experts (nome + foto) e configurar o tempo padrão.
- Dados persistidos em `localStorage`. A rota `/aovivo` exibe o expert em operação (sincronização no mesmo navegador).

## Configuração antes de usar

- `index.html`: constante `CHECKOUT_URL` (link de checkout do Arsenal Pro).
- `aovivo/index.html`: constante `EMBED_URL` (link de embed da transmissão).
- `corujao/index.html`: constante `LIVE_URL` (link da sala/grupo da live).
- Fotos reais dos traders na seção de prova social do `index.html`.

Site estático, sem build. Para rodar localmente: `python -m http.server` na raiz.
