---
description: Aplica o design system de uma referencia analisada no codigo atual
argument-hint: <referencia> [--categoria color|spacing|font-size|motion-easing]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

Aplique o design system da referencia: $ARGUMENTS

## Passo 1 — carregar os tokens

```
./.venv-visual/Scripts/python.exe tools/visual-recon/vrecon_cli.py tokens "<referencia>"
```

Filtre por categoria quando o usuario pedir algo especifico:
`--categoria color` | `color-role` | `spacing` | `font-size` | `gradient` |
`motion-duration` | `motion-easing` | `layout`.

O arquivo pronto fica em `visual-memory/videos/<slug>/design-tokens.css`.

## Passo 2 — aplicar no projeto

1. Identifique onde o projeto define estilo (CSS global, `:root`, tema, etc.).
2. Integre os tokens **sem quebrar o que ja existe**: se o projeto ja tem uma
   convencao de nomes, mapeie os tokens para ela em vez de duplicar variaveis.
3. Substitua valores hardcoded pelos tokens correspondentes nos componentes
   que o usuario pediu — nao faca uma varredura global nao solicitada.

## Passo 3 — verificar contraste

A analise traz `text_contrast_ratio` e `text_wcag_aa`. Se o par de cores que
voce aplicar ficar abaixo de 4.5:1, avise o usuario e sugira o ajuste minimo
para passar em AA.

## Regra

Nunca invente um valor "parecido". Se o token necessario nao existe na analise,
diga isso e pergunte, ou derive explicitamente da escala existente explicando o
raciocinio.
