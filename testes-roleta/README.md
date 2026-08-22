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
