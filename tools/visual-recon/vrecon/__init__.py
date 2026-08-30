"""vrecon — analise e reconstrucao visual de videos de referencia.

Pipeline:
  1. extraction  — extracao completa de frames + perfil de mudanca
  2. temporal    — optical flow, velocidade, aceleracao, curvas de easing
  3. components  — reconhecimento visual + arvore hierarquica
  4. design      — cores, tipografia, layout, efeitos
  5. animation   — engenharia reversa das animacoes -> spec tecnica
  6. memory      — memoria persistente (SQLite + JSON)
  8. validation  — comparacao referencia x versao gerada
"""

__version__ = "1.0.0"

__all__ = [
    "extraction",
    "temporal",
    "components",
    "design",
    "animation",
    "memory",
    "validation",
    "pipeline",
    "config",
]
