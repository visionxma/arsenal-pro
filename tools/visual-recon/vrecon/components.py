"""Etapa 3 — Reconhecimento visual e arvore hierarquica de componentes.

Detecta regioes coerentes no frame e as classifica por geometria, posicao na
tela e contraste, montando a arvore de containers -> filhos.
"""
from __future__ import annotations

import cv2
import numpy as np

from .config import ComponentConfig


def detect_regions(img: np.ndarray, cfg: ComponentConfig) -> list[dict]:
    """Detecta caixas candidatas combinando bordas e blocos de cor uniforme."""
    h, w = img.shape[:2]
    area_total = float(h * w)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    boxes: list[tuple[int, int, int, int]] = []

    # 1) Bordas fechadas -> cards, botoes, inputs, barras.
    edges = cv2.Canny(gray, cfg.edge_low, cfg.edge_high)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        boxes.append(cv2.boundingRect(c))

    # 2) Blocos de cor chapada -> superficies e faixas sem borda desenhada.
    for thresh_type in (cv2.THRESH_BINARY, cv2.THRESH_BINARY_INV):
        _, bw = cv2.threshold(gray, 0, 255, thresh_type | cv2.THRESH_OTSU)
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        contours, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            boxes.append(cv2.boundingRect(c))

    # 3) Faixas horizontais de cor chapada -> header, bottom nav, status bar.
    # Otsu funde essas faixas com o fundo quando o contraste e sutil; detectar
    # por transicao de cor entre linhas as recupera de forma confiavel.
    boxes.extend(_detect_bands(img))

    min_a = cfg.min_area_ratio * area_total
    max_a = cfg.max_area_ratio * area_total

    kept: list[dict] = []
    for (x, y, bw_, bh) in boxes:
        a = float(bw_ * bh)
        if a < min_a or a > max_a:
            continue
        if bw_ < 6 or bh < 6:
            continue
        kept.append(_describe_box(img, x, y, bw_, bh, w, h))

    return _dedupe(kept, cfg.containment_tolerance)


def _detect_bands(img: np.ndarray, min_rows: int = 8) -> list[tuple[int, int, int, int]]:
    """Encontra faixas horizontais de cor homogenea ao longo da tela."""
    h, w = img.shape[:2]
    rows = img.reshape(h, -1, 3).mean(axis=1)          # cor media por linha
    row_std = img.reshape(h, -1, 3).std(axis=1).mean(axis=1)

    bands: list[tuple[int, int, int, int]] = []
    start = 0
    for y in range(1, h):
        # Linha muda de cor de forma marcante -> fronteira de faixa.
        shift = float(np.linalg.norm(rows[y] - rows[y - 1]))
        if shift > 9.0:
            if y - start >= min_rows:
                # So consideramos faixa se as linhas internas forem uniformes.
                if float(np.mean(row_std[start:y])) < 74.0:
                    bands.append((0, start, w, y - start))
            start = y
    if h - start >= min_rows and float(np.mean(row_std[start:h])) < 74.0:
        bands.append((0, start, w, h - start))
    return bands


def _describe_box(
    img: np.ndarray, x: int, y: int, bw: int, bh: int, W: int, H: int
) -> dict:
    roi = img[y : y + bh, x : x + bw]
    mean = roi.reshape(-1, 3).mean(axis=0) if roi.size else np.zeros(3)
    std = float(roi.reshape(-1, 3).std()) if roi.size else 0.0
    b, g, r = (int(round(v)) for v in mean)
    return {
        "x": int(x), "y": int(y), "w": int(bw), "h": int(bh),
        "rel_x": round(x / W, 4), "rel_y": round(y / H, 4),
        "rel_w": round(bw / W, 4), "rel_h": round(bh / H, 4),
        "area_ratio": round((bw * bh) / float(W * H), 6),
        "aspect": round(bw / bh, 3) if bh else 0.0,
        "mean_color": f"#{r:02x}{g:02x}{b:02x}",
        "texture_std": round(std, 2),
    }


def _iou(a: dict, b: dict) -> float:
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    ix1, iy1 = max(a["x"], b["x"]), max(a["y"], b["y"])
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union else 0.0


def _dedupe(boxes: list[dict], tol: int) -> list[dict]:
    """Remove caixas quase identicas vindas dos varios detectores."""
    boxes = sorted(boxes, key=lambda d: d["area_ratio"], reverse=True)
    out: list[dict] = []
    for b in boxes:
        if any(_iou(b, k) > 0.82 for k in out):
            continue
        out.append(b)
    return out


def classify(box: dict, W: int, H: int) -> str:
    """Classifica o componente por geometria e posicao na tela."""
    rx, ry = box["rel_x"], box["rel_y"]
    rw, rh = box["rel_w"], box["rel_h"]
    aspect = box["aspect"]
    bottom = ry + rh

    # Faixas largas coladas no topo/base sao barras de navegacao.
    if rw > 0.85:
        if bottom > 0.88:
            return "bottom-navigation"
        if ry < 0.03 and rh < 0.16:
            return "status-bar"
        if ry < 0.14 and rh < 0.22:
            return "header"
        if rh > 0.72:
            return "screen-background"
        if rh < 0.014:
            return "divider"

    # Modal/overlay: bloco grande e centralizado.
    if rw > 0.7 and 0.18 < rh < 0.75 and rx < 0.16:
        return "modal-overlay"

    # Circular -> avatar, icone ou botao flutuante.
    if 0.82 <= aspect <= 1.22:
        if rw < 0.055:
            return "icon"
        if rw < 0.14:
            return "avatar/botao-circular"
        if bottom > 0.82 and rx > 0.7:
            return "floating-action-button"
        return "elemento-quadrado"

    # Linhas finas e largas -> texto.
    if aspect > 3.4 and rh < 0.035:
        return "texto"
    if aspect > 2.0 and rh < 0.06:
        return "texto/label"

    # Retangulo largo de altura media -> card ou item de lista.
    if rw > 0.55 and 0.05 < rh < 0.3:
        return "card/list-item"
    if 0.2 < rw < 0.6 and 0.03 < rh < 0.1:
        return "botao"
    if rw > 0.3 and rh > 0.3:
        return "imagem/midia"
    if rh > rw * 2:
        return "elemento-vertical"
    return "componente"


def build_tree(boxes: list[dict], W: int, H: int) -> list[dict]:
    """Aninha as caixas por containment, formando a arvore da interface."""
    nodes = []
    for i, b in enumerate(sorted(boxes, key=lambda d: d["area_ratio"], reverse=True)):
        nodes.append({**b, "id": f"n{i}", "type": classify(b, W, H), "children": []})

    roots: list[dict] = []
    for node in nodes:
        parent = None
        # Menor container que engloba o no vira seu pai.
        for cand in nodes:
            if cand is node or cand["area_ratio"] <= node["area_ratio"]:
                continue
            if _contains(cand, node):
                if parent is None or cand["area_ratio"] < parent["area_ratio"]:
                    parent = cand
        if parent is None:
            roots.append(node)
        else:
            parent["children"].append(node)

    for n in nodes:
        n["children"].sort(key=lambda d: (d["y"], d["x"]))
    roots.sort(key=lambda d: (d["y"], d["x"]))
    return roots


def _contains(outer: dict, inner: dict, tol: int = 4) -> bool:
    return (
        outer["x"] - tol <= inner["x"]
        and outer["y"] - tol <= inner["y"]
        and outer["x"] + outer["w"] + tol >= inner["x"] + inner["w"]
        and outer["y"] + outer["h"] + tol >= inner["y"] + inner["h"]
    )


def render_tree(roots: list[dict], max_depth: int = 4, unicode_box: bool = True) -> str:
    """Desenha a arvore em texto, no formato pedido na especificacao.

    unicode_box=False usa apenas ASCII, para consoles Windows (cp1252) que
    nao conseguem imprimir caracteres de box-drawing.
    """
    tee, elbow, pipe = ("├── ", "└── ", " │  ") if unicode_box else ("+-- ", "`-- ", " |  ")
    lines: list[str] = ["Tela"]

    def walk(nodes: list[dict], prefix: str, depth: int) -> None:
        if depth > max_depth:
            return
        for i, n in enumerate(nodes):
            last = i == len(nodes) - 1
            branch = elbow if last else tee
            label = f"{n['type']} ({n['w']}x{n['h']} @ {n['x']},{n['y']})"
            lines.append(f"{prefix}{branch}{label}")
            if n["children"]:
                walk(n["children"], prefix + ("    " if last else pipe), depth + 1)

    walk(roots, " ", 1)
    return "\n".join(lines)


def analyze_frames(frame_paths: list, indices: list[int], cfg: ComponentConfig) -> dict:
    """Roda a deteccao nos keyframes e consolida o resultado."""
    per_frame: list[dict] = []
    for idx in indices:
        if idx >= len(frame_paths):
            continue
        img = cv2.imread(str(frame_paths[idx]), cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        boxes = detect_regions(img, cfg)
        tree = build_tree(boxes, w, h)
        counts: dict[str, int] = {}
        for b in boxes:
            t = classify(b, w, h)
            counts[t] = counts.get(t, 0) + 1
        per_frame.append(
            {
                "frame": idx,
                "component_count": len(boxes),
                "type_counts": counts,
                "tree": tree,
                "tree_text": render_tree(tree),
                "tree_text_ascii": render_tree(tree, unicode_box=False),
            }
        )

    # Frame com maior riqueza estrutural representa a tela principal.
    best = max(per_frame, key=lambda f: f["component_count"], default=None)
    global_counts: dict[str, int] = {}
    for f in per_frame:
        for k, v in f["type_counts"].items():
            global_counts[k] = max(global_counts.get(k, 0), v)

    return {
        "frames_analyzed": len(per_frame),
        "component_types": dict(sorted(global_counts.items(), key=lambda kv: -kv[1])),
        "representative_frame": best["frame"] if best else None,
        "representative_tree_text": best["tree_text"] if best else "",
        "representative_tree_text_ascii": best["tree_text_ascii"] if best else "",
        "representative_tree": best["tree"] if best else [],
        "per_frame": [
            {k: v for k, v in f.items() if k != "tree"} for f in per_frame
        ],
    }
