# Testes e blindagem da Roleta dos Experts

Pasta de QA. **Nada aqui roda em producao.**

## Sandbox isolado

`sandbox/` = copia de `roleta/` com a sincronizacao neutralizada:

| Constante   | Producao                   | Sandbox                    |
|-------------|----------------------------|----------------------------|
| `SYNC_ROOM` | `cj-corujao`               | `cj-SANDBOX-TESTE`         |
| `SYNC_KEY`  | `q1vcjZHdCejBqSJeQSXBKCNC` | `SANDBOX-KEY-NAO-PRODUCAO` |

Isolamento duplo: sala diferente **e** chave diferente (`if (m.k !== SYNC_KEY) return`),
entao nao ha como vazar mensagem para a producao nem receber dela.

Rodar: `cd sandbox && python -m http.server 8777`
- Painel: http://localhost:8777/roleta/admin/
- Roleta: http://localhost:8777/roleta/

Regenerar o sandbox depois de mexer em `roleta/`:
```
cp roleta/index.html roleta/admin/index.html -t testes-roleta/sandbox/roleta/...
sed -i 's/cj-corujao/cj-SANDBOX-TESTE/; s/q1vcjZHdCejBqSJeQSXBKCNC/SANDBOX-KEY-NAO-PRODUCAO/' ...
```

---

## O problema de fundo que foi corrigido

O sync usava `rev = Date.now()` e **substituia a lista inteira**: quem falasse por
ultimo vencia. Com varias maquinas no mesmo login isso quebrava — um notebook que
ficou fora do ar voltava com a lista velha, editava qualquer coisa, ganhava um
`rev` maior (relogio de parede sempre cresce) e empurrava o estado antigo por cima
do que a outra maquina ja tinha corrigido. Relogios desregulados entre maquinas
decidiam o vencedor.

**Agora:**

- `rev` e um **relogio logico (Lamport)**: toda mensagem recebida empurra o relogio
  local para frente, entao ninguem ganha so por ter o relogio adiantado.
- A lista nunca e substituida em bloco: e **mesclada por expert**, campo a campo.
- Remocao vira **lapide** (`cj_experts_tumbas_v1`), com carimbo. Sem lapide, uma
  maquina desatualizada re-adicionava quem ja tinha sido excluido.
- A mesclagem e **comutativa**: mesclar A com B da o mesmo resultado que B com A.
  A ordem de chegada deixou de importar, com quantos painies estiverem abertos.

A roleta (`roleta/index.html`) usa a mesma mesclagem e guarda o maior relogio ja
visto (`cj_rev_visto_v1`) para entregar a um painel recem-aberto — sem esse numero
o painel novo comecaria do zero e **toda edicao dele perderia** para as outras.

---

## Brechas fechadas em "adicionar expert"

| # | Brecha | O que acontecia | Correcao |
|---|--------|-----------------|----------|
| 1 | Cota do localStorage | `setItem` estourava, a excecao subia no meio do fluxo; o operador via "adicionado" e o dado sumia no reload | `save()` devolve `false`, `persistExperts()` desfaz tudo e avisa |
| 2 | Duplo clique | `resizePhoto` e async; dava pra clicar 2x e criar dois | trava `salvandoExpert` + botao desabilitado, com `finally` |
| 3 | Colisao de id | `"e"+Date.now()` — duas maquinas no mesmo ms geravam o MESMO id e o dedupe descartava um expert | `novoIdExpert()` com sufixo aleatorio, checado contra ids e lapides |
| 4 | Sync caido | a adicao ficava so no navegador, sem nunca chegar na roleta | fila `envioPendente` + reenvio automatico + aviso visivel no indicador |
| 5 | Sessao expirada | a roleta descartava o `state` em silencio; o operador achava que salvou | a roleta manda `ack ok:false`, o painel renova a sessao e reenvia |
| 6 | Painel zerado | semeava os 16 padrao e publicava por cima da lista real | nasce vazio, **pede** a lista, adota; so semeia se ninguem responder em 5s |

---

## Regra do sorteio

**A roleta nunca para em quem ja foi sorteado enquanto a rodada nao reiniciar.**

Duas falhas reais foram corrigidas em `roleta/index.html`:

1. **"Forcar proximo sorteado" furava a regra.** O forcado era procurado em
   `activeExperts()` (a lista toda), entao dava pra cair em alguem ja sorteado.
   Agora e procurado no **pool disponivel**; se a pessoa ja saiu, o forcar e
   ignorado com aviso e o sorteio segue aleatorio.
2. **O fallback por indice podia cair em sorteado.** Se a lista mudasse durante o
   giro, `list[pendingIdx]` podia apontar para quem ja tinha saido. Agora o
   fallback so aceita quem ainda nao foi sorteado.

No painel, o select "Forcar proximo sorteado" deixou de listar quem ja saiu —
escolha impossivel nao deve nem aparecer.

Quando todos passam, um **novo ciclo** reinicia a rodada e todos voltam a ser
elegiveis (evitando repetir logo quem fechou o ciclo anterior).

---

## Listas salvas

Nova secao no painel (`Listas salvas`). Guarda formacoes inteiras para poder
testar a vontade e voltar exatamente ao que estava.

- **Salvar lista atual** — snapshot com nome
- **Aplicar** — coloca a lista escolhida no ar
- **Atualizar** — regrava a lista salva com a formacao de agora
- **Renomear** / **Apagar** — apagar descarta so o registro, sem mexer na roleta
- **Backup automatico** — na primeira vez que o painel roda com esta versao, ele
  guarda sozinho a formacao que estava no ar

`Aplicar` nao e substituicao cega: quem sai ganha lapide com o relogio de agora e
quem entra ganha carimbo de agora, senao a mesclagem de outra maquina desfaria a
troca.

---

## Resultados dos testes (Playwright)

Login testado contra o Supabase **real** (`genesisapp360@gmail.com`) — autenticacao
nao toca nos dados da roleta.

### Conflito entre maquinas
| # | Teste | Resultado |
|---|-------|-----------|
| M1 | Mesclagem converge nas duas ordens | PASSOU |
| M2 | Remocao da maquina atualizada sobrevive | PASSOU |
| M3 | Adicao da maquina atualizada sobrevive | PASSOU |
| M4 | Edicao da maquina desatualizada sobrevive | PASSOU |

### Sorteio
| # | Teste | Resultado |
|---|-------|-----------|
| R2 | Forcar alguem ja sorteado e rejeitado | PASSOU |
| R3 | Pool nunca contem sorteado | PASSOU |
| — | **Rodada completa: 15 giros, 15 vencedores unicos, zero repeticao** | PASSOU |
| C3 | Forcar quem ja saiu, em giro real, cai em outra pessoa | PASSOU |

### Robustez de "adicionar"
| # | Teste | Resultado |
|---|-------|-----------|
| G1 | Cota estourada nao corrompe a lista | PASSOU |
| G2 | Triplo clique cria so um expert | PASSOU |
| G4 | Add offline salva local, marca pendente e avisa | PASSOU |
| H2 | Reenvio automatico ao voltar a conexao | PASSOU |
| H5/H7 | Cold start adota a lista, a lapide e o relogio | PASSOU |

### Listas salvas
| # | Teste | Resultado |
|---|-------|-----------|
| L1 | Backup automatico criado sozinho | PASSOU |
| L4 | Salvar formacao atual | PASSOU |
| L6 | Salvar segunda formacao | PASSOU |
| L8 | Restaurar formacao original (12 -> 15, mesmos ids) | PASSOU |
| L9 | Lapides limpas para quem voltou | PASSOU |

### Regressao do painel
Elementos essenciais, menu -> secoes, contadores topo=mini, lista renderizada,
select de forcar, listas renderizadas, configuracoes, funcoes criticas, ausencia
de ids duplicados, busca, filtros, nome duplicado bloqueado, minutos invalidos
bloqueados — **todos passaram**.

### Bugs encontrados pelos testes e corrigidos no meio do caminho
1. `await` dentro de handler nao-async — **quebraria o painel inteiro**
2. Painel zerado ressuscitava experts excluidos (uniao com os 16 padrao)
3. Painel novo herdava relogio 0 — suas edicoes perderiam sempre
4. `renderListas()` nunca era chamada no carregamento

---

## Testar em producao com seguranca

1. No painel, salve a formacao atual em **Listas salvas** (ou confie no backup
   automatico, que ja e criado sozinho)
2. Faca os testes a vontade
3. **Aplicar** na lista salva devolve exatamente a formacao anterior

Alternativa por arquivo (funciona mesmo se o navegador for outro):
`backup/EXPORTAR-estado-producao.js` e `backup/RESTAURAR-estado-producao.js` —
colar no console do painel.

---

## Mobile: scroll horizontal corrigido

A linha do expert nao cabia em 390px: `24 + 38 + selo + pilula + 40 + 3x32 +
gaps` passa de 430px e **todos** os controles eram `flex:none`, entao a linha
vazava a viewport — o nome sumia e a pagina inteira ganhava scroll horizontal.

Os controles viraram um grupo (`.exp-acts`) que desce para a segunda linha em
telas ate 560px. No desktop o layout continua identico.

Antes: `prints/05-mobile-390px-filtro.png` · Depois: `prints/10-mobile-390px-corrigido.png`
Desktop inalterado: `prints/11-desktop-inalterado.png`

Medido em producao a 390px: **0 elementos vazando, sem scroll horizontal**.

---

## Editor de recorte da foto

Antes a foto era cortada sozinha no centro (cover 240x240) e quem estava fora do
quadrado simplesmente sumia. Agora escolher a imagem **abre direto** um editor:

- arrastar para posicionar
- roda do mouse, pinca no celular ou o controle deslizante para aproximar
- girar 90 graus e redefinir
- mascara circular no palco, porque e assim que o avatar aparece na roleta
- o enquadramento e preso: o quadrado fica sempre preenchido, nunca sobra buraco
- previa do resultado ao lado do campo, com **Reajustar** e **Remover**

Saida continua 240x240 JPEG, igual a de antes. Sem biblioteca externa — o CSP so
libera `cdn.jsdelivr.net`, e mais dependencia seria mais risco.

Cancelar ou Escape nao deixa foto pela metade. Se por algum motivo o editor nao
rodar, o corte automatico antigo continua como rede de seguranca.

| # | Teste | Resultado |
|---|-------|-----------|
| C1 | Escala inicial cobre o quadrado | PASSOU |
| C2 | Aproximar atualiza o controle | PASSOU |
| C3 | Arrasto preso (sem buraco) | PASSOU |
| C4 | Girar 90 mantem a cobertura | PASSOU |
| C5 | Redefinir volta ao inicio | PASSOU |
| C6 | Exporta 240x240 JPEG | PASSOU |
| D1 | Aplicar fecha e mostra a previa | PASSOU |
| D2 | Expert salvo com o recorte exato do operador | PASSOU |
| E1 | Cancelar devolve null | PASSOU |
| E2 | Limpar remove previa e arquivo | PASSOU |
| E3 | Escape cancela | PASSOU |

Prints: `prints/12-editor-de-recorte.png`, `prints/13-expert-com-foto-recortada.png`,
`prints/14-editor-recorte-mobile.png`

---

## Rebranding: identidade visual da Safirion

Tokens extraidos do proprio site (`safirion.com`), lidos dos estilos computados —
nao foram inventados:

| Papel | Valor |
|---|---|
| Fundo da pagina | `#03060f` |
| Superficie (card, sidebar, modal) | `#0a1120` |
| Superficie elevada (input) | `#0d1526` |
| Azul primario | `#2389e6` |
| Azul claro (hover/destaque) | `#4ba3f0` |
| Texto secundario | `#8fa5b1` |
| Texto terciario | `#6f818f` |
| Borda | `rgba(255,255,255,.10)` |
| Raio de superficie | 14-16px |
| Titulos | peso 600, tracking negativo (-.02em) |

**O principio da marca e contencao.** No site, a unica coisa com brilho e o CTA
primario; todo o resto e superficie escura com borda de 1px e quase nenhuma
sombra. O painel antigo espalhava gradiente, glow azul e borda colorida por toda
parte — era o oposto da marca.

Removidos: gradiente radial do fundo, gradiente dos botoes, gradiente da barra de
rolagem, bordas azuis genericas, sombras pesadas e a familia Montserrat.
A hierarquia passou a vir de peso e tracking, nao de peso 800/900.

A `Mazzard` do site e comercial e nao pode ser embutida; o proprio site cai em
`-apple-system / Segoe UI / Roboto`. Ficou Poppins, geometrica e proxima do
caracter da Mazzard, que ja estava carregada no painel.

### Navegacao mobile

O botao de menu ficava **dentro** da sidebar. Com ela deslocada para fora da
tela, sobrava uma fatia de 13px na borda esquerda — alvo impossivel no toque.
Agora ha barra superior propria com logo, titulo e indicador de conexao, e o
menu fecha por item, Escape ou toque no fundo, com `aria-expanded` correto.

### Verificacao

| Largura | Resultado |
|---|---|
| 320px | sem overflow, alvos >= 38px |
| 390px | sem overflow, linhas em 2 niveis |
| 768px | 3 indicadores lado a lado, cartao ao vivo horizontal |
| 1440px | layout completo, conteudo limitado a 1080px |
| 1920px | sem overflow, sem esticar demais |

Auditoria do CSS publicado: **0** resquicios do azul antigo (`#00A7FF`),
**0** gradientes, **0** Montserrat, **0** sombras pesadas.
Regressao funcional apos o rebranding: **14/14**.

Corrigido na revisao:
1. `.cmodal-row button` (mais especifica) apagava a borda do botao Cancelar
2. o avatar do cartao ao vivo com `src=""` desenhava o glifo de imagem quebrada

Prints: `brand-01` a `brand-15`; referencia do site em `ref-safirion-01/02`.

---

## Historico da rodada (secao nova)

A folga ao lado de "Tempos & giro" foi preenchida com funcao real. O painel ja
recebia o historico pelo sync, guardava em `cj_hist_v1`, levava no backup e
tinha um botao "Limpar historico" — mas **nunca o exibia**. Havia uma acao para
um dado invisivel. Agora ele aparece com ordem do sorteio, foto, nome e horario,
com o mais recente destacado.

## Rodada de validacao intensa em producao

Feita com ponto de restauracao salvo antes de tudo. 60+ verificacoes.

| Bloco | Cobertura | Resultado |
|---|---|---|
| A | Login real, estado, backup automatico, ponto de restauracao | 7/7 |
| B | Adicionar, duplicado, minutos invalidos, tempo proprio, editar, ativar/desativar, marcar sorteado | 9/9 |
| C | Busca, sem resultado, filtros nos dois conjuntos, busca+filtro, toggle | 9/9 |
| D/E | Editor de recorte: abrir, cobrir, zoom, arrasto preso, girar, redefinir, aplicar, cancelar, salvar com o recorte exato | 7/7 |
| F | Listas: salvar, duplicado, renomear, atualizar, marcar "no ar" | 6/6 |
| G | **Aplicar lista restaurou 20 -> 16 com os mesmos ids e limpou os experts de teste** | 6/6 |
| H | Configuracoes: 5 campos + 3 interruptores + valor invalido + restauracao | 10/10 |
| I | Cota estourada, triplo clique | 2/2 |
| J | Mesclagem multi-maquina converge nas duas ordens | 3/3 |
| K | Link da live: 3 tipos de entrada invalida rejeitados, link real preservado | 4/4 |
| L | Historico: renderiza, contador, estado vazio | 3/3 |
| M | Remover, desfazer, remocao definitiva | 4/4 |
| N | Backup: exporta com experts+cfg+rodada+historico+fotos; restaurar padrao pede confirmacao | 7/7 |
| Q/S/T | Giro real em producao, invariante do sorteio, encerrar, reiniciar | ver abaixo |
| Responsivo | 390 / 834 / 1920 em producao: zero overflow, menu funcional | ok |

### Tres correcoes que a rodada revelou

1. **`Encerrar operacao` nao funcionava com a roleta em segundo plano.**
   O comando so ajustava `timerEndAt` e esperava o `tick()` perceber — mas
   `tick()` roda em `requestAnimationFrame`, que o navegador **pausa em aba de
   fundo**. Como o operador fica no painel, a roleta quase sempre esta em
   segundo plano: ela respondia `ack ok:true` e o cronometro seguia correndo.
   O mesmo afetava o **fim natural do tempo**. Corrigido: `endOp` chama
   `timeUp()` direto e ha um guarda-costas em `setInterval` de 1s.

2. **`Reiniciar rodada` e `Limpar historico` nao pediam confirmacao.**
   Remover UM expert ja pedia, mas devolver TODOS ao sorteio nao. Agora
   perguntam — so quando ha algo a perder, para nao atrapalhar o operador.

3. **Nome de lista salva cortado no mobile.** Passou a quebrar em duas linhas.

### Falsos negativos do teste (nao eram bugs)

- reativar expert: o `render()` recria a linha, e o teste clicava num no obsoleto
- `abrirCropper()` chamado direto nao seta `fotoRecortada` — isso e feito pelo
  handler do input; pelo fluxo real do usuario funcionou 7/7
