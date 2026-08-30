---
description: Analisa um video de referencia (frames, animacoes, design system) e grava na memoria visual
argument-hint: <caminho-do-video> [--titulo "Nome"] [--tags a,b]
allowed-tools: Bash, Read, Glob
---

Analise o video de referencia indicado em: $ARGUMENTS

## Passo 1 — rodar o pipeline

Execute a partir da raiz do projeto (o venv `.venv-visual` ja tem OpenCV e scikit-learn):

```
./.venv-visual/Scripts/python.exe tools/visual-recon/vrecon_cli.py analisar <video> --titulo "<titulo>" --tags "<tags>"
```

Regras:
- Se o usuario nao passou `--titulo`, derive um titulo curto e descritivo do nome do arquivo.
- Se o video for longo (> 60s), acrescente `--max-dimensao 720` para acelerar sem perder proporcao.
- O pipeline extrai TODOS os frames no FPS nativo — nao tente amostrar por segundo.

## Passo 2 — ler o resultado

Leia `visual-memory/videos/<slug>/REPORT.md` e apresente ao usuario:

1. **Estrutura** — a arvore hierarquica de componentes.
2. **Design system** — cores com papeis (fundo/primaria/texto), tipografia, espacamento.
3. **Animacoes** — para cada uma: elemento, propriedades, duracao, curva.
4. **Cortes de cena** — quantas telas distintas o video mostra.

## Passo 3 — apontar o que e reutilizavel

Diga explicitamente quais tokens e padroes de animacao ficaram salvos e como
reaproveita-los depois (`/carregar-memoria-visual <slug>`).

Nao invente valores: tudo que voce afirmar deve vir do REPORT.md ou do
analysis.json gerados. Se algo nao foi detectado, diga que nao foi detectado.
