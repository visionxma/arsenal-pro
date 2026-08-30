"""Configuracao central do pipeline de reconstrucao visual.

Todos os limiares ficam concentrados aqui para permitir tuning sem tocar
na logica dos modulos.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Raiz do projeto (…/Arsenal Pro), 3 niveis acima deste arquivo.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MEMORY_ROOT = PROJECT_ROOT / "visual-memory"
VIDEOS_ROOT = MEMORY_ROOT / "videos"
DB_PATH = MEMORY_ROOT / "index.db"


@dataclass
class ExtractionConfig:
    """Parametros da extracao de frames."""

    # None = mantem o FPS nativo do video (requisito: nao amostrar 1/s).
    fps: float | None = None
    # Mantem resolucao original; se definido, limita o lado maior.
    max_dimension: int | None = None
    # PNG = sem perdas. Qualidade maxima conforme requisito.
    image_format: str = "png"
    # Teto de seguranca para nao explodir o disco em videos longos.
    max_frames: int = 5400


@dataclass
class TemporalConfig:
    """Parametros da analise temporal / optical flow."""

    # Diferenca media por pixel (0-255) acima da qual o frame "mudou".
    change_threshold: float = 1.4
    # Diferenca que caracteriza corte de cena em vez de animacao continua.
    scene_cut_threshold: float = 24.0
    # Magnitude minima de fluxo para considerar que houve movimento real.
    flow_magnitude_floor: float = 0.35
    # Frames minimos para um segmento ser considerado uma animacao.
    min_segment_frames: int = 3
    # Downscale usado no calculo de fluxo (performance sem perder direcao).
    flow_working_width: int = 480


@dataclass
class DesignConfig:
    """Parametros da extracao de design system."""

    palette_size: int = 8
    # Amostragem de pixels por frame no clustering de cor.
    color_sample_pixels: int = 24000
    # Frames usados para montar a paleta global.
    palette_frame_budget: int = 40
    # Distancia RGB para fundir cores quase iguais.
    color_merge_distance: float = 26.0


@dataclass
class ComponentConfig:
    """Parametros da deteccao de componentes."""

    min_area_ratio: float = 0.00035
    max_area_ratio: float = 0.92
    # Agrupa caixas proximas em um mesmo container.
    containment_tolerance: int = 6
    edge_low: int = 55
    edge_high: int = 165


@dataclass
class PipelineConfig:
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    temporal: TemporalConfig = field(default_factory=TemporalConfig)
    design: DesignConfig = field(default_factory=DesignConfig)
    components: ComponentConfig = field(default_factory=ComponentConfig)

    def to_dict(self) -> dict:
        return asdict(self)


def default_config() -> PipelineConfig:
    return PipelineConfig()


def slugify(name: str) -> str:
    """Normaliza um nome para uso como identificador de pasta/chave."""
    keep = []
    prev_dash = False
    for ch in name.strip().lower():
        if ch.isalnum():
            keep.append(ch)
            prev_dash = False
        elif not prev_dash:
            keep.append("-")
            prev_dash = True
    return "".join(keep).strip("-") or "referencia"


def analysis_dir(slug: str) -> Path:
    return VIDEOS_ROOT / slug


def ensure_memory_dirs() -> None:
    VIDEOS_ROOT.mkdir(parents=True, exist_ok=True)


def ffmpeg_binary() -> str:
    return os.environ.get("FFMPEG_BINARY", "ffmpeg")


def ffprobe_binary() -> str:
    return os.environ.get("FFPROBE_BINARY", "ffprobe")
