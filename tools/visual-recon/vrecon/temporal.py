"""Etapa 2 — Analise temporal (optical flow e curvas de animacao).

Responde *como* os elementos se movem: direcao, velocidade, aceleracao,
desaceleracao e qual curva de easing melhor explica o deslocamento.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from .config import TemporalConfig

# Curvas candidatas normalizadas em t e progresso, ambos 0..1.
# O ajuste escolhe a que melhor explica a curva de deslocamento observada.
EASING_MODELS: dict[str, callable] = {
    "linear": lambda t: t,
    "ease-in (quad)": lambda t: t * t,
    "ease-in (cubic)": lambda t: t**3,
    "ease-out (quad)": lambda t: 1 - (1 - t) ** 2,
    "ease-out (cubic)": lambda t: 1 - (1 - t) ** 3,
    "ease-out (quart)": lambda t: 1 - (1 - t) ** 4,
    "ease-in-out (quad)": lambda t: 2 * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 2) / 2,
    "ease-in-out (cubic)": lambda t: 4 * t**3 if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2,
}

# CSS cubic-bezier equivalente, para a especificacao tecnica gerada.
EASING_CSS: dict[str, str] = {
    "linear": "linear",
    "ease-in (quad)": "cubic-bezier(0.11, 0, 0.5, 0)",
    "ease-in (cubic)": "cubic-bezier(0.32, 0, 0.67, 0)",
    "ease-out (quad)": "cubic-bezier(0.5, 1, 0.89, 1)",
    "ease-out (cubic)": "cubic-bezier(0.33, 1, 0.68, 1)",
    "ease-out (quart)": "cubic-bezier(0.25, 1, 0.5, 1)",
    "ease-in-out (quad)": "cubic-bezier(0.45, 0, 0.55, 1)",
    "ease-in-out (cubic)": "cubic-bezier(0.65, 0, 0.35, 1)",
    "spring": "linear(0, 0.45, 0.85, 1.06, 1.02, 1)",
}


def _load_gray(path, width: int) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Nao foi possivel ler o frame: {path}")
    h, w = img.shape[:2]
    if w > width:
        scale = width / w
        img = cv2.resize(img, (width, max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _direction_label(dx: float, dy: float) -> str:
    if abs(dx) < 0.15 and abs(dy) < 0.15:
        return "estatico"
    # Eixo y do frame cresce para baixo.
    angle = math.degrees(math.atan2(-dy, dx))
    if -22.5 <= angle < 22.5:
        return "direita"
    if 22.5 <= angle < 67.5:
        return "cima-direita"
    if 67.5 <= angle < 112.5:
        return "cima"
    if 112.5 <= angle < 157.5:
        return "cima-esquerda"
    if angle >= 157.5 or angle < -157.5:
        return "esquerda"
    if -157.5 <= angle < -112.5:
        return "baixo-esquerda"
    if -112.5 <= angle < -67.5:
        return "baixo"
    return "baixo-direita"


def analyze_segment_flow(
    frame_paths: list,
    seg: dict,
    fps: float,
    cfg: TemporalConfig,
) -> dict:
    """Optical flow denso (Farneback) ao longo de um segmento."""
    s, e = seg["start_frame"], seg["end_frame"]
    indices = list(range(s, min(e + 1, len(frame_paths))))
    if len(indices) < 2:
        return {}

    # Limita o custo em segmentos longos mantendo a forma da curva.
    max_steps = 60
    if len(indices) > max_steps:
        step = len(indices) / max_steps
        indices = [indices[min(int(i * step), len(indices) - 1)] for i in range(max_steps)]

    per_frame: list[dict] = []
    prev = _load_gray(frame_paths[indices[0]], cfg.flow_working_width)

    for idx in indices[1:]:
        curr = _load_gray(frame_paths[idx], cfg.flow_working_width)
        if curr.shape != prev.shape:
            curr = cv2.resize(curr, (prev.shape[1], prev.shape[0]))

        flow = cv2.calcOpticalFlowFarneback(
            prev, curr, None,
            pyr_scale=0.5, levels=3, winsize=17,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
        )
        fx, fy = flow[..., 0], flow[..., 1]
        mag = np.sqrt(fx * fx + fy * fy)
        moving = mag > cfg.flow_magnitude_floor

        coverage = float(np.mean(moving))
        if coverage > 0.0005:
            mean_dx = float(np.mean(fx[moving]))
            mean_dy = float(np.mean(fy[moving]))
            mean_mag = float(np.mean(mag[moving]))
        else:
            mean_dx = mean_dy = mean_mag = 0.0

        per_frame.append(
            {
                "frame": idx,
                "dx": round(mean_dx, 4),
                "dy": round(mean_dy, 4),
                "magnitude": round(mean_mag, 4),
                "coverage": round(coverage, 5),
            }
        )
        prev = curr

    if not per_frame:
        return {}

    mags = np.array([p["magnitude"] for p in per_frame], dtype=np.float64)
    total_dx = float(sum(p["dx"] for p in per_frame))
    total_dy = float(sum(p["dy"] for p in per_frame))

    # Deslocamento acumulado -> curva de progresso 0..1.
    cumulative = np.cumsum(mags)
    total = float(cumulative[-1]) if cumulative.size else 0.0
    progress = (cumulative / total).tolist() if total > 1e-6 else []

    easing, fit_error, is_spring = fit_easing(progress, mags)
    peak_idx = int(np.argmax(mags)) if mags.size else 0
    peak_pos = peak_idx / max(1, len(mags) - 1)

    return {
        "samples": per_frame,
        "mean_magnitude": round(float(np.mean(mags)), 4),
        "peak_magnitude": round(float(np.max(mags)), 4),
        "peak_position": round(peak_pos, 3),
        "total_dx": round(total_dx, 3),
        "total_dy": round(total_dy, 3),
        "direction": _direction_label(total_dx, total_dy),
        "max_coverage": round(max(p["coverage"] for p in per_frame), 5),
        "easing": easing,
        "easing_css": EASING_CSS.get(easing, "ease"),
        "easing_fit_error": round(fit_error, 5),
        "spring_like": is_spring,
        "acceleration_profile": classify_acceleration(mags),
        "velocity_series": [round(m, 4) for m in mags.tolist()],
    }


def fit_easing(progress: list[float], velocities: np.ndarray) -> tuple[str, float, bool]:
    """Ajusta a curva de progresso observada aos modelos candidatos."""
    if len(progress) < 3:
        return "indeterminado", 1.0, False

    n = len(progress)
    ts = np.linspace(0, 1, n)
    obs = np.array(progress, dtype=np.float64)

    best_name, best_err = "linear", float("inf")
    for name, fn in EASING_MODELS.items():
        pred = np.array([fn(float(t)) for t in ts])
        err = float(np.mean((pred - obs) ** 2))
        if err < best_err:
            best_name, best_err = name, err

    # Spring: velocidade que ultrapassa e volta (overshoot/oscilacao) em vez
    # de decair monotonicamente.
    is_spring = detect_spring(velocities)
    if is_spring:
        return "spring", best_err, True
    return best_name, best_err, False


def detect_spring(velocities: np.ndarray) -> bool:
    """Detecta oscilacao caracteristica de mola no perfil de velocidade.

    Uma mola *reacelera* depois de desacelerar (overshoot e volta). Uma
    ease-out apenas decai. Exigimos um vale seguido de um repique real, com
    margem folgada acima do ruido de quantizacao — caso contrario toda
    ease-out com cauda ruidosa seria classificada como spring.
    """
    if velocities.size < 8:
        return False
    v = velocities.astype(np.float64)
    peak = float(np.max(v))
    if peak <= 1e-6:
        return False

    # Suaviza o ruido de compressao antes de procurar a oscilacao.
    kernel = np.ones(3) / 3.0
    smooth = np.convolve(v / peak, kernel, mode="valid")
    peak_idx = int(np.argmax(smooth))
    tail = smooth[peak_idx:]
    if tail.size < 5:
        return False

    trough = float(np.min(tail))
    trough_idx = int(np.argmin(tail))
    after = tail[trough_idx:]
    if after.size < 2:
        return False

    rebound = float(np.max(after))
    # Precisa cair de forma clara e depois repicar de forma clara.
    fell = trough < 0.55
    rose = (rebound - trough) > 0.18 and rebound > trough * 1.6
    return bool(fell and rose)


def classify_acceleration(velocities: np.ndarray) -> str:
    """Classifica o perfil global: acelerando, desacelerando ou constante."""
    if velocities.size < 3:
        return "indeterminado"
    v = velocities.astype(np.float64)
    third = max(1, v.size // 3)
    head = float(np.mean(v[:third]))
    tail = float(np.mean(v[-third:]))
    peak = float(np.max(v))
    if peak <= 1e-6:
        return "sem movimento"

    ratio = (tail - head) / peak
    mid = float(np.mean(v[third : v.size - third])) if v.size > 2 * third else peak
    if mid > head * 1.25 and mid > tail * 1.25:
        return "acelera e desacelera"
    if ratio > 0.18:
        return "acelerando"
    if ratio < -0.18:
        return "desacelerando"
    return "velocidade constante"


def analyze_timeline(
    frame_paths: list,
    segments: list[dict],
    fps: float,
    cfg: TemporalConfig,
) -> list[dict]:
    """Roda a analise de fluxo em todos os segmentos de movimento."""
    results: list[dict] = []
    for seg in segments:
        if seg["kind"] != "transition":
            continue
        flow = analyze_segment_flow(frame_paths, seg, fps, cfg)
        if not flow:
            continue
        # Serie completa fica no relatorio detalhado; o resumo carrega o essencial.
        samples = flow.pop("samples", [])
        results.append(
            {
                **seg,
                "flow": flow,
                "sample_count": len(samples),
            }
        )
    return results
