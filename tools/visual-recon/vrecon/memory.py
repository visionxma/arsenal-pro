"""Etapa 6 — Memoria visual persistente.

Indice SQLite (busca rapida) + artefatos JSON em disco (analise completa).
Permite que "use a referencia do video X" recupere todo o conhecimento salvo.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import DB_PATH, VIDEOS_ROOT, ensure_memory_dirs, slugify

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    slug            TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    source_path     TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    width           INTEGER,
    height          INTEGER,
    fps             REAL,
    duration_s      REAL,
    frame_count     INTEGER,
    orientation     TEXT,
    theme           TEXT,
    primary_color   TEXT,
    background      TEXT,
    animation_count INTEGER,
    component_types TEXT,
    tags            TEXT,
    summary         TEXT,
    analysis_path   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS animations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT NOT NULL,
    anim_id     TEXT,
    element     TEXT,
    types       TEXT,
    duration_ms REAL,
    easing      TEXT,
    direction   TEXT,
    spec_json   TEXT,
    FOREIGN KEY (slug) REFERENCES analyses(slug) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    slug       TEXT NOT NULL,
    category   TEXT NOT NULL,
    name       TEXT NOT NULL,
    value      TEXT NOT NULL,
    FOREIGN KEY (slug) REFERENCES analyses(slug) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_anim_slug ON animations(slug);
CREATE INDEX IF NOT EXISTS idx_tok_slug ON tokens(slug);
CREATE INDEX IF NOT EXISTS idx_tok_cat ON tokens(category);
"""


def connect() -> sqlite3.Connection:
    ensure_memory_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def save_analysis(analysis: dict, tags: list[str] | None = None) -> str:
    """Persiste a analise completa e indexa o que e consultavel."""
    ensure_memory_dirs()
    slug = analysis["slug"]
    out_dir = VIDEOS_ROOT / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    analysis_path = out_dir / "analysis.json"
    analysis_path.write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    meta = analysis.get("video", {})
    ds = analysis.get("design_system", {})
    roles = ds.get("colors", {}).get("roles", {})
    anims = analysis.get("animations", [])
    comp = analysis.get("components", {})

    conn = connect()
    with conn:
        existing = conn.execute(
            "SELECT created_at FROM analyses WHERE slug = ?", (slug,)
        ).fetchone()
        created = existing["created_at"] if existing else _now()

        conn.execute("DELETE FROM animations WHERE slug = ?", (slug,))
        conn.execute("DELETE FROM tokens WHERE slug = ?", (slug,))
        conn.execute(
            """INSERT INTO analyses (
                slug, title, source_path, created_at, updated_at, width, height,
                fps, duration_s, frame_count, orientation, theme, primary_color,
                background, animation_count, component_types, tags, summary,
                analysis_path
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(slug) DO UPDATE SET
                title=excluded.title, source_path=excluded.source_path,
                updated_at=excluded.updated_at, width=excluded.width,
                height=excluded.height, fps=excluded.fps,
                duration_s=excluded.duration_s, frame_count=excluded.frame_count,
                orientation=excluded.orientation, theme=excluded.theme,
                primary_color=excluded.primary_color, background=excluded.background,
                animation_count=excluded.animation_count,
                component_types=excluded.component_types, tags=excluded.tags,
                summary=excluded.summary, analysis_path=excluded.analysis_path
            """,
            (
                slug,
                analysis.get("title", slug),
                meta.get("path", ""),
                created,
                _now(),
                meta.get("width"), meta.get("height"), meta.get("fps"),
                meta.get("duration_s"), meta.get("frame_count"),
                meta.get("orientation"),
                roles.get("theme"),
                roles.get("primary"),
                roles.get("background"),
                len(anims),
                json.dumps(list(comp.get("component_types", {}).keys()), ensure_ascii=False),
                json.dumps(tags or [], ensure_ascii=False),
                analysis.get("summary", ""),
                str(analysis_path),
            ),
        )

        for a in anims:
            conn.execute(
                """INSERT INTO animations
                   (slug, anim_id, element, types, duration_ms, easing, direction, spec_json)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    slug, a.get("id"), a.get("element"),
                    json.dumps(a.get("types", []), ensure_ascii=False),
                    a.get("duration_ms"), a.get("easing"), a.get("direction"),
                    json.dumps(a, ensure_ascii=False),
                ),
            )

        for cat, name, value in _flatten_tokens(analysis):
            conn.execute(
                "INSERT INTO tokens (slug, category, name, value) VALUES (?,?,?,?)",
                (slug, cat, name, value),
            )
    conn.close()
    return str(analysis_path)


def _flatten_tokens(analysis: dict) -> list[tuple[str, str, str]]:
    """Achata o design system em tokens consultaveis."""
    out: list[tuple[str, str, str]] = []
    ds = analysis.get("design_system", {})

    colors = ds.get("colors", {})
    for i, c in enumerate(colors.get("palette", [])):
        out.append(("color", f"palette-{i + 1}", c["hex"]))
    for role, val in (colors.get("roles") or {}).items():
        # 'theme' e um rotulo (claro/escuro), nao uma cor: viraria CSS invalido.
        if isinstance(val, str) and val.startswith("#"):
            out.append(("color-role", role, val))
        elif role == "theme":
            out.append(("meta", "theme", str(val)))

    for g in ds.get("gradients", []) or []:
        out.append(("gradient", g.get("direction", "grad"), g.get("css", "")))

    layout = ds.get("layout", {}) or {}
    for k in ("margin_left_px", "content_width_px", "spacing_base_unit_px"):
        if layout.get(k) is not None:
            out.append(("layout", k, str(layout[k])))
    for v in (layout.get("spacing_scale_px") or [])[:8]:
        out.append(("spacing", f"gap-{v}", f"{v}px"))

    typo = ds.get("typography", {}) or {}
    for v in (typo.get("estimated_font_sizes_px") or [])[:8]:
        out.append(("font-size", f"size-{v}", f"{v}px"))

    for a in analysis.get("animations", []):
        out.append(("motion-duration", a.get("id", "anim"), f"{a.get('duration_ms', 0):.0f}ms"))
        out.append(("motion-easing", a.get("id", "anim"), a.get("easing_css", "ease")))
    return out


def list_analyses() -> list[dict]:
    conn = connect()
    rows = conn.execute(
        """SELECT slug, title, updated_at, width, height, fps, duration_s,
                  orientation, theme, primary_color, animation_count, tags
           FROM analyses ORDER BY updated_at DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_analysis(reference: str) -> dict | None:
    """Carrega por slug, por titulo ou por correspondencia parcial."""
    conn = connect()
    row = conn.execute("SELECT * FROM analyses WHERE slug = ?", (reference,)).fetchone()
    if row is None:
        slug = slugify(reference)
        row = conn.execute("SELECT * FROM analyses WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        row = conn.execute(
            "SELECT * FROM analyses WHERE slug LIKE ? OR title LIKE ? ORDER BY updated_at DESC",
            (f"%{reference}%", f"%{reference}%"),
        ).fetchone()
    conn.close()
    if row is None:
        return None

    path = Path(row["analysis_path"])
    if not path.exists():
        # Fallback: caminho pode ter mudado; procura pelo slug.
        path = VIDEOS_ROOT / row["slug"] / "analysis.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_tokens(reference: str, category: str | None = None) -> list[dict]:
    conn = connect()
    row = conn.execute(
        "SELECT slug FROM analyses WHERE slug = ? OR title LIKE ?",
        (reference, f"%{reference}%"),
    ).fetchone()
    if row is None:
        conn.close()
        return []
    if category:
        rows = conn.execute(
            "SELECT category, name, value FROM tokens WHERE slug = ? AND category = ?",
            (row["slug"], category),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT category, name, value FROM tokens WHERE slug = ?", (row["slug"],)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_animations(
    easing: str | None = None,
    max_duration: float | None = None,
    element: str | None = None,
) -> list[dict]:
    """Busca padroes de animacao reutilizaveis em todas as referencias."""
    q = "SELECT slug, anim_id, element, types, duration_ms, easing, direction FROM animations WHERE 1=1"
    params: list[object] = []
    if easing:
        q += " AND easing LIKE ?"
        params.append(f"%{easing}%")
    if max_duration:
        q += " AND duration_ms <= ?"
        params.append(max_duration)
    if element:
        q += " AND element LIKE ?"
        params.append(f"%{element}%")
    q += " ORDER BY duration_ms"
    conn = connect()
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_analysis(slug: str) -> bool:
    conn = connect()
    with conn:
        cur = conn.execute("DELETE FROM analyses WHERE slug = ?", (slug,))
        conn.execute("DELETE FROM animations WHERE slug = ?", (slug,))
        conn.execute("DELETE FROM tokens WHERE slug = ?", (slug,))
    conn.close()
    return cur.rowcount > 0
