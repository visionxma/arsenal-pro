"""Orquestrador: roda o pipeline completo de analise de um video."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import cv2

from . import animation, components, design, extraction, memory, temporal
from .config import (
    PipelineConfig,
    analysis_dir,
    default_config,
    ensure_memory_dirs,
    slugify,
)


def analyze_video(
    video_path: Path,
    title: str | None = None,
    cfg: PipelineConfig | None = None,
    keep_frames: bool = True,
    tags: list[str] | None = None,
    persist: bool = True,
    progress=print,
) -> dict:
    """Executa as etapas 1-6 e (opcionalmente) grava na memoria visual.

    persist=False roda a analise sem indexar nada: usado na comparacao, para
    que a versao gerada nao vire uma referencia na memoria.
    """
    cfg = cfg or default_config()
    ensure_memory_dirs()

    video_path = Path(video_path)
    title = title or video_path.stem
    slug = slugify(title)
    # Analises efemeras ficam fora de visual-memory/videos para nao poluir
    # o acervo de referencias.
    out_dir = analysis_dir(slug) if persist else _scratch_dir(slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "frames"

    # --- Etapa 1: extracao completa -----------------------------------
    progress("[1/6] Lendo metadados e extraindo frames...")
    meta = extraction.probe(video_path)
    frames = extraction.extract_frames(video_path, frames_dir, meta, cfg.extraction)
    progress(f"      {len(frames)} frames extraidos "
             f"({meta.width}x{meta.height} @ {meta.fps:.2f}fps)")

    profile = extraction.build_change_profile(
        frames, cfg.temporal.change_threshold, cfg.temporal.scene_cut_threshold
    )
    segments = extraction.segment_timeline(
        profile, meta.fps, cfg.temporal.min_segment_frames
    )
    motion = [s for s in segments if s["kind"] == "transition"]
    cuts = [s for s in segments if s["kind"] == "cut"]
    progress(f"      {len(segments)} segmentos | {len(motion)} de movimento | "
             f"{len(cuts)} cortes de cena")

    keyframes = extraction.keyframe_indices(profile, segments, budget=34)

    # --- Etapa 2: analise temporal ------------------------------------
    progress("[2/6] Analisando movimento (optical flow + curvas)...")
    timeline = temporal.analyze_timeline(frames, segments, meta.fps, cfg.temporal)
    progress(f"      {len(timeline)} animacoes medidas")

    # --- Etapa 3: componentes -----------------------------------------
    progress("[3/6] Reconhecendo componentes e hierarquia...")
    comp = components.analyze_frames(frames, keyframes, cfg.components)
    progress(f"      {len(comp.get('component_types', {}))} tipos de componente")

    # --- Etapa 4: design system ---------------------------------------
    progress("[4/6] Extraindo design system...")
    colors = design.extract_palette(frames, keyframes, cfg.design)
    gradients = design.detect_gradients(frames, keyframes)

    rep_idx = comp.get("representative_frame") or (keyframes[0] if keyframes else 0)
    rep_img = cv2.imread(str(frames[rep_idx]), cv2.IMREAD_COLOR)
    if rep_img is not None:
        h, w = rep_img.shape[:2]
        boxes = components.detect_regions(rep_img, cfg.components)
        layout = design.analyze_layout(boxes, w, h)
        typography = design.analyze_typography(rep_img, boxes)
        effects = design.detect_effects(rep_img, boxes)
    else:
        layout, typography, effects = {}, {}, {}
    progress(f"      {len(colors.get('palette', []))} cores | "
             f"{len(gradients)} gradientes | {effects.get('shadows_detected', 0)} sombras")

    # --- Etapa 5: especificacao das animacoes -------------------------
    progress("[5/6] Gerando especificacoes de animacao...")
    specs = animation.build_specs(timeline, frames, profile)

    # --- montagem do resultado ----------------------------------------
    analysis = {
        "slug": slug,
        "title": title,
        "video": meta.to_dict(),
        "config": cfg.to_dict(),
        "timeline": {
            "segments": segments,
            "motion_segments": len(motion),
            "scene_cuts": len(cuts),
            "cut_frames": [c["start_frame"] for c in cuts],
            "keyframes": keyframes,
        },
        "change_profile": profile,
        "components": comp,
        "design_system": {
            "colors": colors,
            "gradients": gradients,
            "layout": layout,
            "typography": typography,
            "effects": effects,
        },
        "animations": specs,
        "motion_analysis": timeline,
    }
    analysis["summary"] = build_summary(analysis)

    # --- Etapa 6: memoria persistente ---------------------------------
    if persist:
        progress("[6/6] Gravando na memoria visual...")
        _write_reports(out_dir, analysis, frames, keyframes)
        if not keep_frames:
            shutil.rmtree(frames_dir, ignore_errors=True)
        path = memory.save_analysis(analysis, tags=tags)
        progress(f"      Memoria: {path}")
    else:
        progress("[6/6] Analise efemera (nao indexada na memoria).")
        shutil.rmtree(out_dir, ignore_errors=True)
    return analysis


def _scratch_dir(slug: str) -> Path:
    import tempfile
    return Path(tempfile.gettempdir()) / "vrecon-scratch" / slug


def _write_reports(out_dir: Path, analysis: dict, frames: list, keyframes: list[int]) -> None:
    """Salva relatorio legivel, tokens e os keyframes escolhidos."""
    ds = analysis["design_system"]

    # Tokens em formato direto de consumo (CSS custom properties).
    tokens_css = _tokens_css(analysis)
    (out_dir / "design-tokens.css").write_text(tokens_css, encoding="utf-8")

    # Especificacoes de animacao em CSS.
    anim_css = "\n\n".join(a["css"] for a in analysis["animations"])
    if anim_css:
        (out_dir / "animations.css").write_text(anim_css, encoding="utf-8")

    (out_dir / "REPORT.md").write_text(build_report(analysis), encoding="utf-8")

    # Copia os keyframes relevantes para consulta futura.
    kf_dir = out_dir / "keyframes"
    kf_dir.mkdir(exist_ok=True)
    for old in kf_dir.glob("*.png"):
        old.unlink()
    for idx in keyframes[:24]:
        if idx < len(frames):
            shutil.copy2(frames[idx], kf_dir / f"key_{idx:06d}.png")


def _tokens_css(analysis: dict) -> str:
    ds = analysis["design_system"]
    roles = ds.get("colors", {}).get("roles", {})
    palette = ds.get("colors", {}).get("palette", [])
    layout = ds.get("layout", {}) or {}
    typo = ds.get("typography", {}) or {}

    lines = [f"/* Design tokens extraidos de: {analysis['title']} */", ":root {"]
    for role, val in roles.items():
        if isinstance(val, str) and val.startswith("#"):
            lines.append(f"  --color-{role}: {val};")
    for i, c in enumerate(palette):
        lines.append(f"  --palette-{i + 1}: {c['hex']}; /* {c['share'] * 100:.1f}% */")
    for g in ds.get("gradients", [])[:3]:
        lines.append(f"  --gradient-{g['direction']}: {g['css']};")

    base = layout.get("spacing_base_unit_px")
    if base:
        lines.append(f"  --space-unit: {base}px;")
    for v in (layout.get("spacing_scale_px") or [])[:8]:
        lines.append(f"  --space-{v}: {v}px;")
    if layout.get("margin_left_px"):
        lines.append(f"  --page-margin: {layout['margin_left_px']}px;")
    for r in (layout.get("border_radius_estimate_px") or [])[:4]:
        lines.append(f"  --radius-{r}: {r}px;")
    for v in (typo.get("estimated_font_sizes_px") or [])[:8]:
        lines.append(f"  --font-{v}: {v}px;")

    for a in analysis.get("animations", []):
        lines.append(f"  --duration-{a['id']}: {a['duration_ms']:.0f}ms;")
        lines.append(f"  --ease-{a['id']}: {a['easing_css']};")
    lines.append("}")
    return "\n".join(lines)


def build_summary(analysis: dict) -> str:
    v = analysis["video"]
    roles = analysis["design_system"].get("colors", {}).get("roles", {})
    anims = analysis["animations"]
    comp = analysis["components"]
    return (
        f"{v['width']}x{v['height']} {v['orientation']} @ {v['fps']:.0f}fps, "
        f"{v['duration_s']:.1f}s. Tema {roles.get('theme', '?')}, "
        f"fundo {roles.get('background', '?')}, primaria {roles.get('primary', '?')}. "
        f"{len(anims)} animacoes, "
        f"{analysis['timeline']['scene_cuts']} cortes de cena, "
        f"{len(comp.get('component_types', {}))} tipos de componente."
    )


def build_report(analysis: dict) -> str:
    """Relatorio Markdown: o briefing de reconstrucao."""
    v = analysis["video"]
    ds = analysis["design_system"]
    colors = ds.get("colors", {})
    roles = colors.get("roles", {})
    layout = ds.get("layout", {}) or {}
    typo = ds.get("typography", {}) or {}
    fx = ds.get("effects", {}) or {}
    comp = analysis["components"]

    L: list[str] = [
        f"# Analise visual: {analysis['title']}",
        "",
        f"> {analysis['summary']}",
        "",
        "## 1. Video",
        "",
        f"- Resolucao: **{v['width']}x{v['height']}** ({v['orientation']})",
        f"- FPS: **{v['fps']:.2f}** | Duracao: **{v['duration_s']:.2f}s** "
        f"| Frames: **{v['frame_count']}**",
        f"- Codec: {v['codec']} | Aspect ratio: {v['aspect_ratio']}",
        "",
        "## 2. Linha do tempo",
        "",
        f"- Segmentos: {len(analysis['timeline']['segments'])}",
        f"- Animacoes detectadas: {analysis['timeline']['motion_segments']}",
        f"- Cortes de cena: {analysis['timeline']['scene_cuts']} "
        f"(frames {analysis['timeline']['cut_frames']})",
        "",
        "| # | inicio | fim | tipo | duracao |",
        "|---|--------|-----|------|---------|",
    ]
    for i, s in enumerate(analysis["timeline"]["segments"], 1):
        L.append(
            f"| {i} | {s['start_s']:.2f}s | {s['end_s']:.2f}s | {s['kind']} | "
            f"{s['duration_ms']:.0f}ms |"
        )

    L += ["", "## 3. Hierarquia de componentes", "", "```",
          comp.get("representative_tree_text_ascii", "(nao detectada)"), "```", "",
          "### Tipos encontrados", ""]
    for t, n in (comp.get("component_types") or {}).items():
        L.append(f"- **{t}**: {n}")

    L += ["", "## 4. Design System", "", "### Cores", ""]
    for role, val in roles.items():
        L.append(f"- `{role}`: **{val}**")
    L += ["", "| cor | presenca | saturacao | luminancia |", "|-----|----------|-----------|------------|"]
    for c in colors.get("palette", []):
        L.append(f"| `{c['hex']}` | {c['share'] * 100:.1f}% | {c['saturation']} | {c['luminance']} |")

    if ds.get("gradients"):
        L += ["", "### Gradientes", ""]
        for g in ds["gradients"]:
            L.append(f"- {g['direction']}: `{g['css']}`")

    L += ["", "### Layout", ""]
    for k, val in layout.items():
        L.append(f"- `{k}`: {val}")

    L += ["", "### Tipografia", ""]
    for k, val in typo.items():
        L.append(f"- `{k}`: {val}")

    L += ["", "### Efeitos", "",
          f"- Nitidez global: {fx.get('global_sharpness')}",
          f"- Sombras detectadas: {fx.get('shadows_detected')}",
          f"- Regioes com glassmorphism: {fx.get('glass_regions_detected')}",
          f"- Camadas de elevacao: {fx.get('elevation_layers')}"]
    for s in (fx.get("shadows") or [])[:3]:
        L.append(f"  - `{s['estimated_css']}`")

    L += ["", "## 5. Animacoes (engenharia reversa)", ""]
    if not analysis["animations"]:
        L.append("_Nenhuma animacao detectada._")
    for a in analysis["animations"]:
        L += [
            f"### {a['id']} — {a['label']}", "",
            f"- **Elemento:** {a['element']}",
            f"- **Janela:** {a['start_s']:.2f}s -> {a['end_s']:.2f}s "
            f"(frames {a['start_frame']}-{a['end_frame']})",
            f"- **Duracao:** {a['duration_ms']:.0f}ms",
            f"- **Curva:** {a['easing']} — `{a['easing_css']}`",
            f"- **Perfil:** {a['acceleration']} | direcao: {a['direction']}",
        ]
        for p in a["properties"]:
            L.append(f"- **{p['property']}**: {p.get('from')} -> {p.get('to')}")
        L += ["", "```css", a["css"], "```", "",
              "```jsx", "// Framer Motion",
              f"<motion.div {_framer_str(a['framer_motion'])} />", "```", ""]

    L += ["", "## 6. Como reconstruir", "",
          "1. Aplicar `design-tokens.css` como base do tema.",
          "2. Montar a arvore de componentes da secao 3 respeitando as proporcoes.",
          "3. Aplicar `animations.css` (ou o snippet Framer Motion) nos elementos.",
          "4. Validar com `/comparar-referencia` contra esta analise.", ""]
    return "\n".join(L)


def _framer_str(fm: dict) -> str:
    return " ".join(f"{k}={{{json.dumps(v)}}}" for k, v in fm.items())
