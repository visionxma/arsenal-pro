---
description: Carrega uma referencia visual ja analisada da memoria persistente
argument-hint: [referencia] [--secao cores|animacoes|layout|arvore]
allowed-tools: Bash, Read
---

Carregue da memoria visual a referencia: $ARGUMENTS

## Se nenhuma referencia foi informada

Liste o que existe e pergunte qual usar:

```
./.venv-visual/Scripts/python.exe tools/visual-recon/vrecon_cli.py listar
```

## Se uma referencia foi informada

```
./.venv-visual/Scripts/python.exe tools/visual-recon/vrecon_cli.py carregar "<referencia>" --secao tudo
```

A busca aceita slug, titulo ou correspondencia parcial.

Depois leia `visual-memory/videos/<slug>/REPORT.md` para o detalhamento completo
e apresente ao usuario:

- resumo da referencia (resolucao, tema, cores principais);
- arvore de componentes;
- animacoes com duracao e curva;
- caminho dos tokens (`design-tokens.css`) e das animacoes (`animations.css`).

## Importante

A partir daqui, mantenha esse conhecimento como contexto ativo: ao construir
qualquer interface nesta conversa, use esses tokens e essas curvas de animacao
em vez de valores inventados.
