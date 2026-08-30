"""Etapa 4 — Extracao do Design System.

Deriva cores, tipografia (metricas), layout/espacamento e efeitos visuais a
partir dos keyframes.
"""
from __future__ import annotations

import cv2
import numpy as np
from sklearn.cluster import KMeans

from .config import DesignConfig


# ---------------------------------------------------------------- cores

def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _relative_luminance(r: int, g: int, b: int) -> float:
    def ch(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast_ratio(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    l1, l2 = _relative_luminance(*c1), _relative_luminance(*c2)
    hi, lo = max(l1, l2), min(l1, l2)
    return round((hi + 0.05) / (lo + 0.05), 2)


def extract_palette(
    frame_paths: list, indices: list[int], cfg: DesignConfig
) -> dict:
    """Paleta global via k-means em espaco LAB (perceptualmente uniforme)."""
    budget = indices[: cfg.palette_frame_budget] or indices
    samples: list[np.ndarray] = []

    for idx in budget:
        if idx >= len(frame_paths):
            continue
        img = cv2.imread(str(frame_paths[idx]), cv2.IMREAD_COLOR)
        if img is None:
            continue
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).reshape(-1, 3)
        per = max(1, cfg.color_sample_pixels // max(1, len(budget)))
        if lab.shape[0] > per:
            sel = np.random.default_rng(11).choice(lab.shape[0], per, replace=False)
            lab = lab[sel]
        samples.append(lab)

    if not samples:
        return {"palette": [], "roles": {}}

    data = np.vstack(samples).astype(np.float32)
    k = min(cfg.palette_size, max(2, len(np.unique(data, axis=0))))
    km = KMeans(n_clusters=k, n_init=6, random_state=11).fit(data)

    counts = np.bincount(km.labels_, minlength=k).astype(np.float64)
    weights = counts / counts.sum()

    entries: list[dict] = []
    for i, center in enumerate(km.cluster_centers_):
        lab_px = np.uint8([[center]])
        bgr = cv2.cvtColor(lab_px, cv2.COLOR_LAB2BGR)[0][0]
        b, g, r = int(bgr[0]), int(bgr[1]), int(bgr[2])
        hsv = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0][0]
        entries.append(
            {
                "hex": _rgb_to_hex(r, g, b),
                "rgb": [r, g, b],
                "share": round(float(weights[i]), 4),
                "hue": int(hsv[0]) * 2,
                "saturation": round(int(hsv[1]) / 255, 3),
                "value": round(int(hsv[2]) / 255, 3),
                "luminance": round(_relative_luminance(r, g, b), 4),
            }
        )

    entries = _merge_close(entries, cfg.color_merge_distance)
    entries.sort(key=lambda e: -e["share"])
    return {"palette": entries, "roles": assign_roles(entries)}


def _merge_close(entries: list[dict], min_dist: float) -> list[dict]:
    out: list[dict] = []
    for e in sorted(entries, key=lambda x: -x["share"]):
        dup = None
        for o in out:
            d = float(np.linalg.norm(np.array(e["rgb"]) - np.array(o["rgb"])))
            if d < min_dist:
                dup = o
                break
        if dup:
            dup["share"] = round(dup["share"] + e["share"], 4)
        else:
            out.append(e)
    return out


def assign_roles(palette: list[dict]) -> dict:
    """Atribui papeis semanticos (background, primaria, texto, acento)."""
    if not palette:
        return {}

    roles: dict[str, object] = {}
    # A cor mais presente e o fundo.
    bg = palette[0]
    roles["background"] = bg["hex"]
    dark_ui = bg["luminance"] < 0.18
    roles["theme"] = "escuro" if dark_ui else "claro"

    # Superficie: segunda cor mais presente, proxima do fundo em luminancia.
    surfaces = [
        p for p in palette[1:]
        if abs(p["luminance"] - bg["luminance"]) < 0.22 and p["saturation"] < 0.45
    ]
    if surfaces:
        roles["surface"] = surfaces[0]["hex"]

    # Texto: maior contraste contra o fundo.
    bg_rgb = tuple(bg["rgb"])
    text = max(palette, key=lambda p: contrast_ratio(tuple(p["rgb"]), bg_rgb))
    roles["text"] = text["hex"]
    roles["text_contrast_ratio"] = contrast_ratio(tuple(text["rgb"]), bg_rgb)
    roles["text_wcag_aa"] = roles["text_contrast_ratio"] >= 4.5

    # Primaria: cor saturada com presenca relevante (accent da marca).
    accents = [p for p in palette if p["saturation"] > 0.35 and p["value"] > 0.28]
    accents.sort(key=lambda p: (p["saturation"] * 0.6 + p["share"] * 0.4), reverse=True)
    if accents:
        roles["primary"] = accents[0]["hex"]
        roles["primary_contrast_on_bg"] = contrast_ratio(
            tuple(accents[0]["rgb"]), bg_rgb
        )
        if len(accents) > 1:
            roles["secondary"] = accents[1]["hex"]
    return roles


def detect_gradients(frame_paths: list, indices: list[int]) -> list[dict]:
    """Detecta gradientes por variacao monotonica suave de cor."""
    found: list[dict] = []
    for idx in indices[:12]:
        if idx >= len(frame_paths):
            continue
        img = cv2.imread(str(frame_paths[idx]), cv2.IMREAD_COLOR)
        if img is None:
            continue
        small = cv2.resize(img, (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32)

        for axis, name in ((0, "vertical"), (1, "horizontal")):
            line = small.mean(axis=1 - axis)  # perfil medio ao longo do eixo
            diffs = np.diff(line, axis=0)
            if diffs.size == 0:
                continue
            # Gradiente: passos consistentes no mesmo sentido e sem degraus.
            signs = np.sign(diffs.mean(axis=1))
            monotonic = float(np.mean(signs == signs[0])) if signs.size else 0.0
            span = float(np.linalg.norm(line[-1] - line[0]))
            step_var = float(np.std(np.linalg.norm(diffs, axis=1)))
            if monotonic > 0.86 and span > 26 and step_var < 5.5:
                c0 = line[0].astype(int)
                c1 = line[-1].astype(int)
                found.append(
                    {
                        "frame": idx,
                        "direction": name,
                        "from": _rgb_to_hex(c0[2], c0[1], c0[0]),
                        "to": _rgb_to_hex(c1[2], c1[1], c1[0]),
                        "delta": round(span, 2),
                        "css": (
                            f"linear-gradient({'180deg' if name == 'vertical' else '90deg'}, "
                            f"{_rgb_to_hex(c0[2], c0[1], c0[0])}, "
                            f"{_rgb_to_hex(c1[2], c1[1], c1[0])})"
                        ),
                    }
                )
    return found[:6]


# ---------------------------------------------------------------- layout

def analyze_layout(boxes: list[dict], W: int, H: int) -> dict:
    """Deriva grid, espacamentos e margens recorrentes."""
    if not boxes:
        return {}

    # Faixas full-bleed (header, nav, fundo) comecam em x=0 e enviesariam a
    # margem para zero. A margem real e definida pelo conteudo dentro delas.
    content = [b for b in boxes if b["rel_w"] < 0.97] or boxes

    # Numa UI coexistem dois recuos: a margem da pagina (onde comecam os
    # containers) e o padding interno (onde comeca o texto dentro deles). O
    # texto e mais numeroso, entao votar pela moda simples devolve o padding e
    # esconde a margem. A margem da pagina e o recuo *mais externo* que se
    # repete no conteudo; a moda serve para descartar outliers de 1 ocorrencia.
    edges = _recurring_edges([b["x"] for b in content], tolerance=6, min_count=2)
    margin_left = min(edges) if edges else _mode_within([b["x"] for b in content], 6)

    # A borda direita do texto varia com o comprimento do conteudo, entao ela
    # nao e um indicador confiavel de margem. So aceitamos a medida da direita
    # se algum elemento realmente terminar perto da borda oposta; caso
    # contrario assumimos layout simetrico, que e o padrao esmagador em UI.
    right_edges = _recurring_edges(
        [b["x"] + b["w"] for b in content], tolerance=6, min_count=2
    )
    margin_right = margin_left
    if right_edges:
        candidate = W - max(right_edges)
        if candidate <= margin_left * 2.5:
            margin_right = candidate

    # O proximo recuo recorrente para dentro e o padding dos containers.
    inner_pad = None
    deeper = sorted(e for e in edges if e > margin_left)
    if deeper:
        inner_pad = deeper[0] - margin_left

    # Espacamento vertical entre elementos empilhados.
    ordered = sorted(content, key=lambda b: b["y"])
    gaps: list[int] = []
    for a, b in zip(ordered, ordered[1:]):
        gap = b["y"] - (a["y"] + a["h"])
        # Faixas adjacentes (header colado no conteudo) geram gap 0, que nao
        # e espacamento de layout — poluiria a escala com um token inutil.
        if 2 <= gap < H * 0.25:
            gaps.append(gap)

    spacing_scale = _infer_scale(gaps)
    radii = _estimate_radius(boxes)

    return {
        "margin_left_px": margin_left,
        "margin_right_px": margin_right,
        "container_padding_px": inner_pad,
        "content_width_px": W - margin_left - max(0, margin_right),
        "vertical_gaps_px": sorted(set(gaps))[:14],
        "spacing_base_unit_px": spacing_scale["base"],
        "spacing_scale_px": spacing_scale["scale"],
        "border_radius_estimate_px": radii,
        "columns_detected": _detect_columns(boxes, W),
    }


def _recurring_edges(values: list[int], tolerance: int, min_count: int) -> list[int]:
    """Recuos que aparecem pelo menos `min_count` vezes (ignora outliers)."""
    edges: list[int] = []
    for v in sorted(set(values)):
        count = sum(1 for o in values if abs(o - v) <= tolerance)
        if count >= min_count and not any(abs(v - e) <= tolerance for e in edges):
            edges.append(int(v))
    return edges


def _mode_within(values: list[int], tolerance: int) -> int:
    if not values:
        return 0
    best_val, best_count = values[0], 0
    for v in values:
        c = sum(1 for o in values if abs(o - v) <= tolerance)
        if c > best_count:
            best_val, best_count = v, c
    return int(best_val)


def _infer_scale(gaps: list[int]) -> dict:
    """Encontra a unidade base (4/8px etc.) que explica os espacamentos."""
    if not gaps:
        return {"base": 0, "scale": []}
    best_base, best_score = 0, -1.0
    for base in (4, 6, 8, 10, 12, 16):
        score = sum(1 for g in gaps if g % base <= 1 or base - (g % base) <= 1)
        norm = score / len(gaps)
        if norm > best_score:
            best_base, best_score = base, norm
    # Arredondar pode zerar gaps pequenos; um token de espacamento 0 nao serve
    # para nada, entao mantemos apenas valores positivos.
    scale = sorted(
        v for v in {int(round(g / best_base) * best_base) for g in gaps if g > 0} if v > 0
    )
    return {"base": best_base if best_score > 0.5 else 0, "scale": scale[:10]}


def _detect_columns(boxes: list[dict], W: int) -> int:
    """Conta colunas por agrupamento dos centros horizontais."""
    wide = [b for b in boxes if b["rel_w"] < 0.6]
    if len(wide) < 3:
        return 1
    centers = sorted((b["x"] + b["w"] / 2) / W for b in wide)
    clusters = 1
    for a, b in zip(centers, centers[1:]):
        if b - a > 0.13:
            clusters += 1
    return min(clusters, 6)


def _estimate_radius(boxes: list[dict]) -> list[int]:
    """Estimativa grosseira de raio de borda a partir da escala dos blocos."""
    radii = set()
    for b in boxes:
        if b["rel_w"] > 0.5 and b["rel_h"] > 0.04:
            radii.add(int(round(min(b["w"], b["h"]) * 0.06)))
    return sorted(r for r in radii if r > 0)[:6]


# ---------------------------------------------------------- tipografia

def analyze_typography(img: np.ndarray, boxes: list[dict]) -> dict:
    """Metricas tipograficas a partir das regioes de texto detectadas."""
    text_like = [
        b for b in boxes
        if b["aspect"] > 2.0 and b["rel_h"] < 0.06 and b["rel_w"] > 0.05
    ]
    if not text_like:
        return {"samples": 0}

    heights = sorted(b["h"] for b in text_like)
    # Alturas recorrentes viram a escala tipografica.
    scale = _cluster_values(heights, tolerance=3)

    left_aligned = sum(1 for b in text_like if b["rel_x"] < 0.14)
    centered = sum(
        1 for b in text_like if abs((b["rel_x"] + b["rel_w"] / 2) - 0.5) < 0.06
    )

    lines = sorted(text_like, key=lambda b: b["y"])
    leadings: list[int] = []
    for a, b in zip(lines, lines[1:]):
        d = b["y"] - a["y"]
        if 0 < d < 220:
            leadings.append(d)

    return {
        "samples": len(text_like),
        "glyph_height_px": scale,
        "estimated_font_sizes_px": [int(round(h * 1.34)) for h in scale],
        "line_height_px": sorted(set(leadings))[:8],
        "alignment": (
            "centralizado" if centered > left_aligned else "esquerda"
        ),
        "align_left_count": left_aligned,
        "align_center_count": centered,
    }


def _cluster_values(values: list[int], tolerance: int) -> list[int]:
    out: list[int] = []
    for v in sorted(values):
        if not out or abs(v - out[-1]) > tolerance:
            out.append(int(v))
    return out[:8]


# ------------------------------------------------------------- efeitos

def detect_effects(img: np.ndarray, boxes: list[dict]) -> dict:
    """Detecta sombras, blur/glassmorphism e elevacao."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]

    # Nitidez global via variancia do laplaciano.
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    shadows: list[dict] = []
    glass: list[dict] = []

    for b in boxes[:24]:
        x, y, bw, bh = b["x"], b["y"], b["w"], b["h"]
        if bw < 24 or bh < 24:
            continue

        # Sombra: faixa logo abaixo da caixa mais escura que o entorno.
        band_y = min(h, y + bh + max(3, bh // 12))
        below = gray[y + bh : band_y, x : x + bw]
        outside = gray[max(0, y - 6) : y, x : x + bw]
        if below.size and outside.size:
            drop = float(np.mean(outside)) - float(np.mean(below))
            if drop > 7.0:
                shadows.append(
                    {
                        "region": {"x": x, "y": y, "w": bw, "h": bh},
                        "intensity": round(drop, 2),
                        "estimated_css": _shadow_css(drop, bh),
                    }
                )

        # Glassmorphism: interior de baixa nitidez mas com variacao de cor.
        roi = gray[y : y + bh, x : x + bw]
        if roi.size > 400:
            local_sharp = float(cv2.Laplacian(roi, cv2.CV_64F).var())
            color_std = float(img[y : y + bh, x : x + bw].reshape(-1, 3).std())
            if local_sharp < sharpness * 0.32 and color_std > 9:
                glass.append(
                    {
                        "region": {"x": x, "y": y, "w": bw, "h": bh},
                        "local_sharpness": round(local_sharp, 2),
                        "estimated_css": "backdrop-filter: blur(14px); background: rgba(255,255,255,0.10)",
                    }
                )

    return {
        "global_sharpness": round(sharpness, 2),
        "shadows_detected": len(shadows),
        "shadows": shadows[:6],
        "glass_regions_detected": len(glass),
        "glassmorphism": glass[:4],
        "elevation_layers": min(4, 1 + len(shadows) // 2),
    }


def _shadow_css(intensity: float, box_h: int) -> str:
    blur = max(6, int(box_h * 0.09))
    offset = max(2, int(blur * 0.42))
    alpha = min(0.42, round(intensity / 100.0 + 0.1, 2))
    return f"box-shadow: 0 {offset}px {blur}px rgba(0,0,0,{alpha})"
