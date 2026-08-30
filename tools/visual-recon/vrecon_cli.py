#!/usr/bin/env python
"""CLI do sistema de analise e reconstrucao visual.

Uso:
  python vrecon_cli.py analisar <video> [--titulo T] [--tags a,b] [--sem-frames]
  python vrecon_cli.py listar
  python vrecon_cli.py carregar <referencia> [--secao cores|animacoes|layout|arvore|tudo]
  python vrecon_cli.py tokens <referencia> [--categoria color|spacing|motion-easing|...]
  python vrecon_cli.py buscar-animacoes [--easing E] [--max-duracao MS] [--elemento X]
  python vrecon_cli.py comparar <referencia> <video-ou-analise-gerada>
  python vrecon_cli.py remover <slug>
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

# Garante que o pacote seja importavel quando chamado por caminho absoluto.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Console do Windows costuma ser cp1252 e quebra ao imprimir a arvore/acentos.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from vrecon import memory, pipeline, validation  # noqa: E402
from vrecon.config import default_config  # noqa: E402


def cmd_analisar(args: argparse.Namespace) -> int:
    video = Path(args.video)
    if not video.exists():
        print(f"ERRO: video nao encontrado: {video}")
        return 1
    cfg = default_config()
    if args.max_dimensao:
        cfg.extraction.max_dimension = args.max_dimensao

    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    analysis = pipeline.analyze_video(
        video,
        title=args.titulo,
        cfg=cfg,
        keep_frames=not args.sem_frames,
        tags=tags,
    )
    print("\n" + "=" * 60)
    print(f"ANALISE CONCLUIDA: {analysis['slug']}")
    print("=" * 60)
    print(analysis["summary"])
    print(f"\nRelatorio: visual-memory/videos/{analysis['slug']}/REPORT.md")
    print(f"Tokens:    visual-memory/videos/{analysis['slug']}/design-tokens.css")
    if analysis["animations"]:
        print(f"Animacoes: visual-memory/videos/{analysis['slug']}/animations.css")
        print("\nAnimacoes detectadas:")
        for a in analysis["animations"]:
            print(f"  - {a['id']}: {a['label']} | {a['duration_ms']:.0f}ms | "
                  f"{a['easing']} | {a['element']}")
    return 0


def cmd_listar(_: argparse.Namespace) -> int:
    rows = memory.list_analyses()
    if not rows:
        print("Nenhuma analise na memoria visual ainda.")
        print("Rode: python vrecon_cli.py analisar <video>")
        return 0
    print(f"{len(rows)} referencia(s) na memoria visual:\n")
    for r in rows:
        tags = ", ".join(json.loads(r["tags"] or "[]"))
        print(f"  {r['slug']}")
        print(f"    {r['width']}x{r['height']} @ {r['fps']:.0f}fps | {r['duration_s']:.1f}s "
              f"| {r['orientation']} | tema {r['theme']}")
        print(f"    primaria {r['primary_color']} | {r['animation_count']} animacoes"
              + (f" | tags: {tags}" if tags else ""))
        print(f"    atualizado: {r['updated_at']}")
        print()
    return 0


def cmd_carregar(args: argparse.Namespace) -> int:
    a = memory.load_analysis(args.referencia)
    if a is None:
        print(f"Referencia nao encontrada: {args.referencia}")
        print("Use 'listar' para ver o que esta na memoria.")
        return 1

    sec = args.secao
    print(f"# {a['title']} ({a['slug']})")
    print(a["summary"])
    print()

    ds = a.get("design_system", {})
    if sec in ("tudo", "cores"):
        print("## Cores")
        for role, val in (ds.get("colors", {}).get("roles") or {}).items():
            print(f"  {role}: {val}")
        print("  paleta:", ", ".join(c["hex"] for c in ds.get("colors", {}).get("palette", [])))
        print()
    if sec in ("tudo", "layout"):
        print("## Layout")
        for k, v in (ds.get("layout") or {}).items():
            print(f"  {k}: {v}")
        print("## Tipografia")
        for k, v in (ds.get("typography") or {}).items():
            print(f"  {k}: {v}")
        print()
    if sec in ("tudo", "arvore"):
        print("## Hierarquia")
        print(a.get("components", {}).get("representative_tree_text", ""))
        print()
    if sec in ("tudo", "animacoes"):
        print("## Animacoes")
        for an in a.get("animations", []):
            print(f"  {an['id']}: {an['label']} | {an['duration_ms']:.0f}ms | "
                  f"{an['easing']} ({an['easing_css']}) | {an['element']}")
            for p in an["properties"]:
                print(f"      {p['property']}: {p.get('from')} -> {p.get('to')}")
        print()
    if sec == "tudo":
        print(f"Relatorio completo: visual-memory/videos/{a['slug']}/REPORT.md")
    return 0


def cmd_tokens(args: argparse.Namespace) -> int:
    toks = memory.get_tokens(args.referencia, args.categoria)
    if not toks:
        print(f"Nenhum token encontrado para: {args.referencia}")
        return 1
    by_cat: dict[str, list[dict]] = {}
    for t in toks:
        by_cat.setdefault(t["category"], []).append(t)
    for cat, items in by_cat.items():
        print(f"\n[{cat}]")
        for t in items:
            print(f"  --{t['name']}: {t['value']};")
    return 0


def cmd_buscar_animacoes(args: argparse.Namespace) -> int:
    rows = memory.search_animations(
        easing=args.easing, max_duration=args.max_duracao, element=args.elemento
    )
    if not rows:
        print("Nenhuma animacao corresponde aos filtros.")
        return 0
    print(f"{len(rows)} animacao(oes) encontrada(s):\n")
    for r in rows:
        types = ", ".join(json.loads(r["types"] or "[]"))
        print(f"  [{r['slug']}] {r['anim_id']}: {types}")
        print(f"    {r['duration_ms']:.0f}ms | {r['easing']} | {r['element']} | {r['direction']}")
    return 0


def cmd_comparar(args: argparse.Namespace) -> int:
    ref = memory.load_analysis(args.referencia)
    if ref is None:
        print(f"Referencia nao encontrada: {args.referencia}")
        return 1

    gen_path = Path(args.gerado)
    if gen_path.suffix.lower() == ".json":
        gen = json.loads(gen_path.read_text(encoding="utf-8"))
    elif gen_path.exists():
        # E um video/captura: analisa na hora, sem sujar a memoria.
        print("Analisando a versao gerada para comparar...\n")
        gen = pipeline.analyze_video(
            gen_path,
            title=f"{ref['slug']}--gerado",
            keep_frames=False,
            persist=False,
        )
    else:
        gen = memory.load_analysis(args.gerado)
        if gen is None:
            print(f"Versao gerada nao encontrada: {args.gerado}")
            return 1

    result = validation.compare(ref, gen)
    print("\n" + "=" * 60)
    print(f"COMPARACAO: {ref['slug']}  x  {gen.get('slug', 'gerado')}")
    print("=" * 60)
    print(f"Score geral: {result['overall_score'] * 100:.1f}%")
    print(f"Veredito:    {result['verdict']}")
    print()
    print(f"  cores      {result['colors']['score'] * 100:5.1f}%")
    print(f"  layout     {result['layout']['score'] * 100:5.1f}%")
    print(f"  animacoes  {result['animations']['score'] * 100:5.1f}%")
    print(f"  estrutura  {result['structure']['score'] * 100:5.1f}%")

    if result["issues"]:
        print(f"\n{result['issue_count']} ajuste(s) necessario(s):")
        for i in result["issues"]:
            hint = i.get("hint") or i.get("problem") or ""
            print(f"  [{i['area']}] {hint}")
    else:
        print("\nNenhuma divergencia relevante encontrada.")

    out = Path(ref.get("slug", "comparacao"))
    from vrecon.config import VIDEOS_ROOT
    rp = VIDEOS_ROOT / out / "ultima-comparacao.json"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDetalhes: {rp}")
    return 0


def cmd_remover(args: argparse.Namespace) -> int:
    ok = memory.delete_analysis(args.slug)
    print("Removido." if ok else f"Nao encontrado: {args.slug}")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(
        prog="vrecon", description="Analise e reconstrucao visual de videos de referencia"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analisar", help="analisa um video e grava na memoria visual")
    a.add_argument("video")
    a.add_argument("--titulo", default=None)
    a.add_argument("--tags", default="")
    a.add_argument("--sem-frames", action="store_true",
                   help="descarta os frames apos a analise (economiza disco)")
    a.add_argument("--max-dimensao", type=int, default=None,
                   help="limita o lado maior dos frames (padrao: resolucao original)")
    a.set_defaults(func=cmd_analisar)

    l = sub.add_parser("listar", help="lista as referencias na memoria")
    l.set_defaults(func=cmd_listar)

    c = sub.add_parser("carregar", help="carrega uma referencia da memoria")
    c.add_argument("referencia")
    c.add_argument("--secao", default="tudo",
                   choices=["tudo", "cores", "animacoes", "layout", "arvore"])
    c.set_defaults(func=cmd_carregar)

    t = sub.add_parser("tokens", help="lista os design tokens de uma referencia")
    t.add_argument("referencia")
    t.add_argument("--categoria", default=None)
    t.set_defaults(func=cmd_tokens)

    b = sub.add_parser("buscar-animacoes", help="busca padroes de animacao reutilizaveis")
    b.add_argument("--easing", default=None)
    b.add_argument("--max-duracao", type=float, default=None)
    b.add_argument("--elemento", default=None)
    b.set_defaults(func=cmd_buscar_animacoes)

    k = sub.add_parser("comparar", help="compara a referencia com a versao gerada")
    k.add_argument("referencia")
    k.add_argument("gerado", help="video, screenshot-video ou analysis.json da versao gerada")
    k.set_defaults(func=cmd_comparar)

    r = sub.add_parser("remover", help="remove uma referencia da memoria")
    r.add_argument("slug")
    r.set_defaults(func=cmd_remover)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
