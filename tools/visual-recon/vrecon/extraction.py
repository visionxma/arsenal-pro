"""Etapa 1 — Extracao completa de frames.

Extrai a sequencia inteira no FPS nativo (nao 1 frame/s), preservando
resolucao e ordem temporal, e constroi um perfil de mudanca por frame que
alimenta as etapas seguintes.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .config import ExtractionConfig, ffmpeg_binary, ffprobe_binary


@dataclass
class VideoMeta:
    path: str
    width: int
    height: int
    fps: float
    duration: float
    frame_count: int
    codec: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "width": self.width,
            "height": self.height,
            "fps": round(self.fps, 4),
            "duration_s": round(self.duration, 4),
            "frame_count": self.frame_count,
            "codec": self.codec,
            "aspect_ratio": round(self.width / self.height, 4) if self.height else 0,
            "orientation": _orientation(self.width, self.height),
        }


def _orientation(w: int, h: int) -> str:
    if h == 0:
        return "desconhecida"
    ratio = w / h
    if ratio < 0.85:
        return "retrato"
    if ratio > 1.2:
        return "paisagem"
    return "quadrada"


def _parse_rate(rate: str) -> float:
    """Converte '30000/1001' -> 29.97."""
    if not rate:
        return 0.0
    if "/" in rate:
        num, _, den = rate.partition("/")
        try:
            d = float(den)
            return float(num) / d if d else 0.0
        except ValueError:
            return 0.0
    try:
        return float(rate)
    except ValueError:
        return 0.0


def probe(video_path: Path) -> VideoMeta:
    """Le metadados reais do container via ffprobe."""
    if not video_path.exists():
        raise FileNotFoundError(f"Video nao encontrado: {video_path}")

    cmd = [
        ffprobe_binary(), "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate,r_frame_rate,nb_frames,codec_name,duration",
        "-show_entries", "format=duration",
        "-of", "json", str(video_path),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}

    fps = _parse_rate(stream.get("avg_frame_rate", "")) or _parse_rate(
        stream.get("r_frame_rate", "")
    )
    duration = float(stream.get("duration") or fmt.get("duration") or 0.0)

    try:
        frame_count = int(stream.get("nb_frames") or 0)
    except (TypeError, ValueError):
        frame_count = 0
    if frame_count <= 0 and fps and duration:
        frame_count = int(round(fps * duration))

    return VideoMeta(
        path=str(video_path),
        width=int(stream.get("width") or 0),
        height=int(stream.get("height") or 0),
        fps=fps or 30.0,
        duration=duration,
        frame_count=frame_count,
        codec=str(stream.get("codec_name") or "desconhecido"),
    )


def extract_frames(
    video_path: Path,
    out_dir: Path,
    meta: VideoMeta,
    cfg: ExtractionConfig,
) -> list[Path]:
    """Extrai a sequencia completa de frames para out_dir."""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    filters: list[str] = []
    target_fps = cfg.fps
    # Teto de seguranca: se o video for longo demais, reduz o FPS de captura
    # de forma explicita em vez de truncar a linha do tempo pela metade.
    if meta.frame_count > cfg.max_frames and meta.duration > 0:
        target_fps = cfg.max_frames / meta.duration
    if target_fps:
        filters.append(f"fps={target_fps:.6f}")
    if cfg.max_dimension:
        m = cfg.max_dimension
        filters.append(
            f"scale='if(gt(iw,ih),min({m},iw),-2)':'if(gt(iw,ih),-2,min({m},ih))'"
        )

    def build_cmd(passthrough_flag: list[str]) -> list[str]:
        cmd = [ffmpeg_binary(), "-y", "-i", str(video_path)]
        if filters:
            cmd += ["-vf", ",".join(filters)]
        # Preserva a cadencia real dos frames, sem duplicar nem derrubar.
        cmd += passthrough_flag
        if cfg.image_format == "png":
            cmd += ["-compression_level", "1"]
        else:
            cmd += ["-q:v", "2"]
        cmd += [str(out_dir / f"frame_%06d.{cfg.image_format}")]
        return cmd

    # -fps_mode substituiu -vsync; builds antigos so entendem o segundo.
    proc = subprocess.run(build_cmd(["-fps_mode", "passthrough"]),
                          capture_output=True, text=True)
    if proc.returncode != 0 and "fps_mode" in proc.stderr:
        proc = subprocess.run(build_cmd(["-vsync", "0"]),
                              capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Falha do FFmpeg na extracao:\n{proc.stderr[-1800:]}")

    frames = sorted(out_dir.glob(f"frame_*.{cfg.image_format}"))
    if not frames:
        raise RuntimeError("FFmpeg terminou sem produzir frames.")
    return frames


def build_change_profile(
    frames: list[Path],
    change_threshold: float,
    scene_cut_threshold: float,
) -> list[dict]:
    """Perfil de mudanca frame a frame.

    Para cada frame calcula a diferenca media absoluta contra o anterior e o
    classifica como 'static', 'transition' ou 'cut'. E isso que permite
    analisar cada alteracao visual relevante em vez de amostrar por tempo.
    """
    profile: list[dict] = []
    prev_small: np.ndarray | None = None

    for idx, fpath in enumerate(frames):
        img = cv2.imread(str(fpath), cv2.IMREAD_COLOR)
        if img is None:
            continue
        # Preserva o aspecto: uma grade fixa 160x90 distorce video retrato
        # e dilui ainda mais mudancas locais.
        h, w = img.shape[:2]
        tw = 192
        th = max(1, int(round(h * (tw / w))))
        small = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)

        if prev_small is None:
            delta = 0.0
            local = 0.0
            region = None
        else:
            diff = np.abs(gray - prev_small)
            delta = float(np.mean(diff))
            # Um card animado ocupa fracao pequena de uma tela mobile: a media
            # global o afoga em ruido. Medimos tambem a regiao mais alterada,
            # que e o que caracteriza uma animacao localizada.
            local, region = _peak_region_change(diff)

        # 'delta' global identifica corte de cena (a tela inteira muda);
        # 'local' identifica animacao de componente.
        if delta >= scene_cut_threshold:
            kind = "cut"
        elif local >= change_threshold:
            kind = "transition"
        else:
            kind = "static"

        entry = {
            "index": idx,
            "file": fpath.name,
            "delta": round(delta, 4),
            "local_delta": round(local, 4),
            "kind": kind,
        }
        if region is not None:
            entry["change_region"] = region
        profile.append(entry)
        prev_small = gray

    return profile


def _peak_region_change(diff: np.ndarray, grid: int = 8) -> tuple[float, dict | None]:
    """Maior mudanca media entre celulas de uma grade sobre o frame.

    Retorna a intensidade e a celula (normalizada 0..1) onde ocorreu, o que
    tambem indica *onde* na tela a animacao acontece.
    """
    h, w = diff.shape
    ch, cw = max(1, h // grid), max(1, w // grid)
    best = 0.0
    best_cell = None
    for gy in range(grid):
        for gx in range(grid):
            y0, x0 = gy * ch, gx * cw
            cell = diff[y0 : y0 + ch, x0 : x0 + cw]
            if cell.size == 0:
                continue
            m = float(np.mean(cell))
            if m > best:
                best = m
                best_cell = {
                    "x": round(x0 / w, 3),
                    "y": round(y0 / h, 3),
                    "w": round(cw / w, 3),
                    "h": round(ch / h, 3),
                }
    return best, best_cell


def segment_timeline(
    profile: list[dict],
    fps: float,
    min_segment_frames: int,
) -> list[dict]:
    """Agrupa frames contiguos em segmentos de animacao e repouso."""
    if not profile:
        return []

    # Histerese: curvas ease-out terminam com deslocamento sub-pixel que cai
    # abaixo do limiar. Sem isso, a cauda da animacao e cortada e a duracao
    # medida sai menor que a real. Frames 'static' logo apos um 'transition'
    # sao reabsorvidos enquanto ainda houver residuo de movimento.
    profile = _apply_hysteresis(profile)

    segments: list[dict] = []
    start = 0
    current = profile[0]["kind"]

    def close(end_idx: int, kind: str) -> None:
        length = end_idx - start + 1
        # Segmentos de movimento curtos demais viram ruido; mantemos apenas
        # os que tem duracao suficiente para caracterizar uma animacao.
        if kind == "transition" and length < min_segment_frames:
            return
        window = profile[start : end_idx + 1]
        deltas = [p["delta"] for p in window]
        locals_ = [p.get("local_delta", p["delta"]) for p in window]
        segments.append(
            {
                "kind": kind,
                "start_frame": start,
                "end_frame": end_idx,
                "frame_count": length,
                "start_s": round(start / fps, 4) if fps else 0.0,
                "end_s": round((end_idx + 1) / fps, 4) if fps else 0.0,
                "duration_ms": round((length / fps) * 1000, 2) if fps else 0.0,
                "peak_delta": round(max(deltas), 4) if deltas else 0.0,
                "mean_delta": round(float(np.mean(deltas)), 4) if deltas else 0.0,
                "peak_local_delta": round(max(locals_), 4) if locals_ else 0.0,
            }
        )

    for i in range(1, len(profile)):
        kind = profile[i]["kind"]
        # 'cut' sempre encerra o segmento: e uma troca de tela, nao animacao.
        if kind != current or kind == "cut":
            close(i - 1, current)
            start = i
            current = kind
    close(len(profile) - 1, current)

    return segments


def _apply_hysteresis(
    profile: list[dict],
    release_floor: float = 0.08,
    max_tail: int = 20,
) -> list[dict]:
    """Estende segmentos de movimento pela cauda de desaceleracao.

    Curvas ease-out terminam de forma assintotica: os ultimos frames andam
    fracoes de pixel e ficam muito abaixo do limiar de entrada. Ancorar a
    liberacao numa fracao do pico nao funciona (a cauda e, por definicao,
    uma fracao pequena do pico) — o corte correto e junto ao piso de ruido:
    seguimos dentro da animacao enquanto houver movimento mensuravel.
    """
    out = [dict(p) for p in profile]
    n = len(out)
    i = 0
    while i < n:
        if out[i]["kind"] != "transition":
            i += 1
            continue

        j = i
        while j < n and out[j]["kind"] == "transition":
            j += 1

        tail = 0
        while j < n and tail < max_tail and out[j]["kind"] == "static":
            if out[j].get("local_delta", out[j]["delta"]) < release_floor:
                break
            out[j]["kind"] = "transition"
            out[j]["hysteresis"] = True
            j += 1
            tail += 1
        i = max(j, i + 1)
    return out


def keyframe_indices(profile: list[dict], segments: list[dict], budget: int) -> list[int]:
    """Escolhe os frames mais representativos para amostragem pesada.

    Prioriza inicio/meio/fim de cada segmento e os picos de mudanca, para
    que as etapas caras (cor, componentes) vejam os momentos que importam.
    """
    picks: set[int] = set()

    # Telas em repouso sao as melhores para ler estrutura e design system:
    # nada esta em movimento, entao os componentes aparecem inteiros.
    resting = [s for s in segments if s["kind"] == "static"]
    for seg in sorted(resting, key=lambda s: -s["frame_count"]):
        s, e = seg["start_frame"], seg["end_frame"]
        # Evita as bordas do segmento, onde ainda pode haver residuo de movimento.
        pad = max(1, seg["frame_count"] // 6)
        picks.update({min(e, s + pad), (s + e) // 2, max(s, e - pad)})

    # Segmentos de movimento entram para cobrir inicio/meio/fim da animacao.
    for seg in segments:
        if seg["kind"] == "static":
            continue
        s, e = seg["start_frame"], seg["end_frame"]
        picks.update({s, (s + e) // 2, e})

    ranked = sorted(profile, key=lambda p: p.get("local_delta", p["delta"]), reverse=True)
    for p in ranked:
        if len(picks) >= budget:
            break
        picks.add(p["index"])

    if not picks and profile:
        picks.add(0)

    limit = len(profile) - 1
    return sorted(i for i in picks if 0 <= i <= limit)
