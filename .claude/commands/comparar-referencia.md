---
description: Compara a interface reconstruida com o video de referencia e corrige as divergencias
argument-hint: <referencia> <url-ou-video-da-versao-gerada>
allowed-tools: Bash, Read, Edit, Write, Glob
---

Compare a versao gerada com a referencia: $ARGUMENTS

## Passo 1 — obter a captura da versao gerada

Se o usuario passou um **video** ou um **analysis.json**, use direto.

Se passou uma **URL/pagina local**, capture antes com Playwright:
1. `mcp__playwright__browser_navigate` para a pagina.
2. `mcp__playwright__browser_resize` com a MESMA resolucao da referencia
   (veja `width`/`height` no `analysis.json` — ex.: 1080x1920).
3. Dispare a interacao que aciona a animacao e capture a sequencia com
   `mcp__playwright__browser_take_screenshot` em varios momentos, ou grave a
   tela se o usuario tiver um gravador.

A resolucao precisa bater: o comparador reprova de saida quando o aspect ratio
diverge, porque isso distorce todas as demais medidas.

## Passo 2 — rodar a comparacao

```
./.venv-visual/Scripts/python.exe tools/visual-recon/vrecon_cli.py comparar "<referencia>" "<video-ou-json>"
```

A analise da versao gerada e efemera: nao polui a memoria de referencias.

## Passo 3 — corrigir automaticamente

O comando devolve um score por area (cores, layout, animacoes, estrutura) e uma
lista de ajustes acionaveis. Para cada item:

- **cores** — trocar o token no CSS pelo valor da referencia;
- **layout** — ajustar margem, largura de conteudo ou numero de colunas;
- **animacao** — corrigir `duration` e `easing` para os valores medidos;
- **estrutura** — adicionar o componente ausente.

Aplique as correcoes e rode a comparacao de novo. Repita ate o score parar de
subir ou atingir "aprovado".

## Passo 4 — relatar

Mostre ao usuario:
- score antes e depois;
- o que foi corrigido;
- o que continua divergente e por que (algumas diferencas sao limitacao de
  medicao, nao erro de implementacao — diga isso claramente em vez de fingir
  fidelidade total).
