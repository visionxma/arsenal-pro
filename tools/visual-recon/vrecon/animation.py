"""Etapa 5 — Engenharia reversa das animacoes.

Converte os segmentos de movimento em especificacoes tecnicas reutilizaveis
(tipo de animacao, propriedades, duracao, curva) e em codigo pronto.
"""
from __future__ import annotations

import cv2
import numpy as np

from .temporal import EASING_CSS


def _region_stats(img: np.ndarray, region: dict | None) -> tuple[float, float]:
    """Brilho medio e area coberta pela regiao de mudanca."""
    if img is None:
        return 0.0, 0.0
    h, w = img.shape[:2]
    if not region:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray)), 1.0
    x = int(region["x"] * w)
    y = int(region["y"] * h)
    rw = max(1, int(region["w"] * w))
    rh = max(1, int(region["h"] * h))
    roi = img[y : y + rh, x : x + rw]
    if roi.size == 0:
        return 0.0, 0.0
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray)), (rw * rh) / float(w * h)


def classify_animation(
    seg: dict,
    frame_paths: list,
    profile: list[dict],
) -> dict:
    """Deduz o tipo de animacao a partir do fluxo e da mudanca de intensidade."""
    flow = seg.get("flow", {})
    s, e = seg["start_frame"], seg["end_frame"]

    first = cv2.imread(str(frame_paths[s]), cv2.IMREAD_COLOR) if s < len(frame_paths) else None
    last = cv2.imread(str(frame_paths[e]), cv2.IMREAD_COLOR) if e < len(frame_paths) else None

    region = None
    for p in profile[s : e + 1]:
        if p.get("change_region"):
            region = p["change_region"]
            break

    b0, area = _region_stats(first, region)
    b1, _ = _region_stats(last, region)
    brightness_delta = b1 - b0

    dx, dy = flow.get("total_dx", 0.0), flow.get("total_dy", 0.0)
    travel = float(np.hypot(dx, dy))
    coverage = flow.get("max_coverage", 0.0)

    types: list[str] = []
    props: list[dict] = []

    # Deslocamento direcional consistente -> slide / translate.
    if travel > 1.2:
        axis = "translateY" if abs(dy) >= abs(dx) else "translateX"
        amount = dy if axis == "translateY" else dx
        # O fluxo mede no frame reduzido; reescala para pixels reais.
        scale_back = 1.0
        if first is not None:
            scale_back = first.shape[1] / 480.0
        px = abs(amount) * scale_back
        direction = flow.get("direction", "")
        types.append("slide")
        props.append(
            {
                "property": axis,
                "from": f"{px:+.0f}px" if amount < 0 else f"{-px:+.0f}px",
                "to": "0px",
                "observed_direction": direction,
            }
        )

    # Mudanca de luminancia sem deslocamento -> fade.
    if abs(brightness_delta) > 3.0:
        types.append("fade")
        props.append(
            {
                "property": "opacity",
                "from": "0" if brightness_delta > 0 else "1",
                "to": "1" if brightness_delta > 0 else "0",
                "brightness_delta": round(brightness_delta, 2),
            }
        )

    # Cobertura crescente com pouco deslocamento liquido -> scale.
    if coverage > 0.06 and travel < 1.4 and abs(brightness_delta) <= 3.0:
        types.append("scale")
        props.append({"property": "transform: scale", "from": "0.92", "to": "1"})

    if flow.get("spring_like"):
        types.append("spring")

    # Movimento amplo e uniforme na tela toda -> scroll/parallax.
    if coverage > 0.55 and travel > 2.5:
        types.append("scroll/parallax")

    if not types:
        types.append("mudanca-de-estado")

    return {
        "types": sorted(set(types)),
        "properties": props,
        "change_region": region,
        "region_area_ratio": round(area, 4),
        "brightness_delta": round(brightness_delta, 2),
    }


def build_spec(
    seg: dict,
    frame_paths: list,
    profile: list[dict],
    index: int,
) -> dict:
    """Monta a especificacao tecnica completa de uma animacao."""
    flow = seg.get("flow", {})
    cls = classify_animation(seg, frame_paths, profile)
    duration = seg.get("duration_ms", 0.0)
    easing = flow.get("easing", "indeterminado")
    css_easing = EASING_CSS.get(easing, "ease")

    label = "+".join(cls["types"])
    return {
        "id": f"anim_{index:02d}",
        "element": _guess_element(cls, seg),
        "types": cls["types"],
        "label": label,
        "start_s": seg.get("start_s"),
        "end_s": seg.get("end_s"),
        "start_frame": seg["start_frame"],
        "end_frame": seg["end_frame"],
        "duration_ms": duration,
        "easing": easing,
        "easing_css": css_easing,
        "easing_fit_error": flow.get("easing_fit_error"),
        "acceleration": flow.get("acceleration_profile"),
        "direction": flow.get("direction"),
        "spring_like": flow.get("spring_like", False),
        "properties": cls["properties"],
        "change_region": cls["change_region"],
        "region_area_ratio": cls["region_area_ratio"],
        "peak_velocity": flow.get("peak_magnitude"),
        "peak_position": flow.get("peak_position"),
        "css": _to_css(f"anim_{index:02d}", cls, duration, css_easing),
        "framer_motion": _to_framer(cls, duration, easing, flow),
        "spec_text": _to_text(cls, seg, flow),
    }


def _guess_element(cls: dict, seg: dict) -> str:
    """Nomeia o elemento animado pela posicao e tamanho da regiao."""
    r = cls.get("change_region")
    area = cls.get("region_area_ratio", 0.0)
    if not r:
        return "tela"
    cy = r["y"] + r["h"] / 2
    if area > 0.5:
        return "tela inteira"
    if cy < 0.16:
        return "header / topo"
    if cy > 0.85:
        return "bottom navigation / rodape"
    if area > 0.12:
        return "card / painel principal"
    return "componente"


def _to_css(name: str, cls: dict, duration: float, easing: str) -> str:
    """Gera keyframes CSS equivalentes."""
    from_parts: list[str] = []
    to_parts: list[str] = []
    transforms_from: list[str] = []
    transforms_to: list[str] = []

    for p in cls["properties"]:
        prop = p["property"]
        if prop == "opacity":
            from_parts.append(f"opacity: {p['from']}")
            to_parts.append(f"opacity: {p['to']}")
        elif prop.startswith("translate"):
            transforms_from.append(f"{prop}({p['from']})")
            transforms_to.append(f"{prop}({p['to']})")
        elif prop.startswith("transform: scale"):
            transforms_from.append(f"scale({p['from']})")
            transforms_to.append(f"scale({p['to']})")

    if transforms_from:
        from_parts.append(f"transform: {' '.join(transforms_from)}")
        to_parts.append(f"transform: {' '.join(transforms_to)}")
    if not from_parts:
        from_parts, to_parts = ["opacity: 0"], ["opacity: 1"]

    fr = "; ".join(from_parts)
    to = "; ".join(to_parts)
    return (
        f"@keyframes {name} {{\n"
        f"  from {{ {fr}; }}\n"
        f"  to   {{ {to}; }}\n"
        f"}}\n"
        f".{name} {{\n"
        f"  animation: {name} {duration:.0f}ms {easing} both;\n"
        f"}}"
    )


def _to_framer(cls: dict, duration: float, easing: str, flow: dict) -> dict:
    """Gera props equivalentes para Framer Motion."""
    initial: dict[str, object] = {}
    animate: dict[str, object] = {}

    for p in cls["properties"]:
        prop = p["property"]
        if prop == "opacity":
            initial["opacity"] = float(p["from"])
            animate["opacity"] = float(p["to"])
        elif prop == "translateY":
            initial["y"] = p["from"]
            animate["y"] = 0
        elif prop == "translateX":
            initial["x"] = p["from"]
            animate["x"] = 0
        elif prop.startswith("transform: scale"):
            initial["scale"] = float(p["from"])
            animate["scale"] = float(p["to"])

    if flow.get("spring_like"):
        transition = {"type": "spring", "stiffness": 260, "damping": 22}
    else:
        transition = {
            "duration": round(duration / 1000.0, 3),
            "ease": EASING_CSS.get(easing, "easeOut"),
        }
    return {"initial": initial or {"opacity": 0}, "animate": animate or {"opacity": 1},
            "transition": transition}


def _to_text(cls: dict, seg: dict, flow: dict) -> str:
    """Especificacao legivel, no formato pedido no briefing."""
    lines = [
        f"Elemento:\n{_guess_element(cls, seg)}",
        "",
        f"Tipo:\n{', '.join(cls['types'])}",
        "",
    ]
    for p in cls["properties"]:
        if p["property"] == "opacity":
            lines += [f"Entrada:\nopacity {p['from']} -> {p['to']}", ""]
        else:
            lines += [f"Movimento:\n{p['property']} {p['from']} -> {p['to']}", ""]
    lines += [
        f"Duracao:\n{seg.get('duration_ms', 0):.0f}ms",
        "",
        f"Curva:\n{flow.get('easing', 'indeterminado')} "
        f"({EASING_CSS.get(flow.get('easing', ''), 'ease')})",
        "",
        f"Perfil:\n{flow.get('acceleration_profile', '-')}",
    ]
    return "\n".join(lines)


def build_specs(
    timeline: list[dict],
    frame_paths: list,
    profile: list[dict],
) -> list[dict]:
    return [
        build_spec(seg, frame_paths, profile, i + 1)
        for i, seg in enumerate(timeline)
    ]
