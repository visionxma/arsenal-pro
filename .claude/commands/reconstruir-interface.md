---
description: Reconstroi uma interface a partir de uma referencia visual analisada
argument-hint: <referencia> [o que construir]
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

Reconstrua a interface com base na referencia: $ARGUMENTS

## Passo 1 — SEMPRE consultar a memoria primeiro

Antes de escrever qualquer linha de codigo:

```
./.venv-visual/Scripts/python.exe tools/visual-recon/vrecon_cli.py carregar "<referencia>" --secao tudo
```

Leia tambem:
- `visual-memory/videos/<slug>/REPORT.md` — analise completa
- `visual-memory/videos/<slug>/design-tokens.css` — tokens prontos
- `visual-memory/videos/<slug>/animations.css` — keyframes prontos
- `visual-memory/videos/<slug>/keyframes/` — imagens de referencia (use Read para ver)

Se a referencia nao existir na memoria, pare e diga ao usuario para rodar
`/analisar-video` antes.

## Passo 2 — reconstruir de verdade

Nao copie apenas a aparencia. Recrie:

- **Arquitetura** — componentes reutilizaveis seguindo a arvore hierarquica
  detectada, nao um bloco monolitico de HTML.
- **Tokens** — importe/aplique `design-tokens.css`. Use `var(--color-primary)`,
  `var(--space-N)`; nunca redigite valores hex soltos no meio do codigo.
- **Responsividade** — respeite as proporcoes medidas (`aspect_ratio`,
  `margin_left_px`, `content_width_px`); adapte para outras larguras sem
  quebrar o ritmo visual.
- **Estados** — hover, focus, active, disabled, loading e vazio.
- **Animacoes** — use exatamente a duracao e a curva medidas. Se a analise diz
  317ms com `cubic-bezier(0.5, 1, 0.89, 1)`, use esses valores.
- **Microinteracoes** — o que o video mostra ao tocar/rolar/abrir.
- **Acessibilidade** — respeite o contraste medido; se `text_wcag_aa` for
  false na analise, corrija e avise o usuario que a referencia falhava em AA.

## Passo 3 — validar

Depois de construir, rode `/comparar-referencia <referencia> <sua-versao>`
para medir a fidelidade e corrigir as divergencias apontadas.

## Regra

Toda decisao visual deve ser rastreavel a um numero da analise. Se algo nao
estiver na analise, diga que esta assumindo e explique a suposicao.
