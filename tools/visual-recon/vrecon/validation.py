"""Etapa 8 — Validacao: referencia x versao gerada.

Compara a analise do video original com a captura da interface reconstruida
e aponta, de forma acionavel, o que ainda diverge.
"""
from __future__ import annotations

import cv2
import numpy as np

from .design import contrast_ratio


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def color_distance(hex_a: str, hex_b: str) -> float:
    """Distancia perceptual (LAB) entre duas cores."""
    a = np.uint8([[list(_hex_to_rgb(hex_a))[::-1]]])
    b = np.uint8([[list(_hex_to_rgb(hex_b))[::-1]]])
    la = cv2.cvtColor(a, cv2.COLOR_BGR2LAB)[0][0].astype(float)
    lb = cv2.cvtColor(b, cv2.COLOR_BGR2LAB)[0][0].astype(float)
    return float(np.linalg.norm(la - lb))


def compare_palettes(ref: dict, gen: dict, tolerance: float = 18.0) -> dict:
    """Confere se cada cor relevante da referencia existe na versao gerada."""
    ref_pal = [c["hex"] for c in ref.get("palette", [])]
    gen_pal = [c["hex"] for c in gen.get("palette", [])]

    matched, missing = [], []
    for rc in ref_pal:
        best = min((color_distance(rc, gc), gc) for gc in gen_pal) if gen_pal else (999, None)
        if best[0] <= tolerance:
            matched.append({"reference": rc, "generated": best[1], "delta": round(best[0], 2)})
        else:
            missing.append({
                "reference": rc,
                "closest": best[1],
                "delta": round(best[0], 2),
                "problem": "cor ausente na versao gerada",
                "hint": (
                    f"Cor {rc} da referencia nao aparece no resultado "
                    f"(mais proxima: {best[1]}, distancia {best[0]:.1f})"
                ),
            })

    roles_ref = ref.get("roles", {})
    roles_gen = gen.get("roles", {})
    role_diffs = []
    for role in ("background", "surface", "text", "primary", "secondary"):
        a, b = roles_ref.get(role), roles_gen.get(role)
        if isinstance(a, str) and isinstance(b, str):
            d = color_distance(a, b)
            role_diffs.append(
                {
                    "role": role, "reference": a, "generated": b,
                    "delta": round(d, 2), "ok": d <= tolerance,
                }
            )
        elif isinstance(a, str) and b is None:
            role_diffs.append({"role": role, "reference": a, "generated": None, "ok": False})

    score = len(matched) / len(ref_pal) if ref_pal else 1.0
    return {
        "score": round(score, 3),
        "matched": matched,
        "missing": missing,
        "roles": role_diffs,
    }


def compare_layout(ref: dict, gen: dict, tolerance_ratio: float = 0.06) -> dict:
    """Compara margens, largura de conteudo e ritmo de espacamento."""
    issues: list[dict] = []
    checks = 0
    passed = 0

    for key in ("margin_left_px", "content_width_px", "spacing_base_unit_px"):
        a, b = ref.get(key), gen.get(key)
        if a is None or b is None or not a:
            continue
        checks += 1
        delta = abs(a - b) / max(1.0, abs(a))
        if delta <= tolerance_ratio:
            passed += 1
        else:
            issues.append(
                {
                    "property": key, "reference": a, "generated": b,
                    "delta_pct": round(delta * 100, 1),
                    "hint": f"Ajustar {key}: referencia {a}px, gerado {b}px",
                }
            )

    ref_cols, gen_cols = ref.get("columns_detected"), gen.get("columns_detected")
    if ref_cols and gen_cols:
        checks += 1
        if ref_cols == gen_cols:
            passed += 1
        else:
            issues.append(
                {
                    "property": "columns", "reference": ref_cols, "generated": gen_cols,
                    "hint": f"Grid deveria ter {ref_cols} coluna(s), gerado tem {gen_cols}",
                }
            )

    return {
        "score": round(passed / checks, 3) if checks else 1.0,
        "checks": checks,
        "issues": issues,
    }


def compare_animations(ref: list[dict], gen: list[dict], tol_ms: float = 90.0) -> dict:
    """Compara duracao, curva e tipo das animacoes."""
    issues: list[dict] = []
    matches: list[dict] = []

    unused = list(gen)
    for r in ref:
        # Pareia pela animacao gerada com duracao mais proxima e tipo compativel.
        best, best_cost = None, float("inf")
        for g in unused:
            type_overlap = len(set(r.get("types", [])) & set(g.get("types", [])))
            cost = abs(r.get("duration_ms", 0) - g.get("duration_ms", 0))
            if type_overlap == 0:
                cost += 400
            if cost < best_cost:
                best, best_cost = g, cost
        if best is None:
            issues.append({"reference": r.get("id"), "problem": "sem animacao correspondente",
                           "hint": f"Falta animacao {r.get('label')} de {r.get('duration_ms'):.0f}ms"})
            continue
        unused.remove(best)

        d_delta = abs(r.get("duration_ms", 0) - best.get("duration_ms", 0))
        same_easing = (r.get("easing") == best.get("easing"))
        ok = d_delta <= tol_ms and same_easing
        entry = {
            "reference": r.get("id"), "generated": best.get("id"),
            "duration_ref_ms": r.get("duration_ms"),
            "duration_gen_ms": best.get("duration_ms"),
            "duration_delta_ms": round(d_delta, 1),
            "easing_ref": r.get("easing"), "easing_gen": best.get("easing"),
            "ok": ok,
        }
        matches.append(entry)
        if d_delta > tol_ms:
            issues.append({
                "reference": r.get("id"),
                "problem": "duracao divergente",
                "hint": f"Ajustar duracao para ~{r.get('duration_ms'):.0f}ms "
                        f"(gerado: {best.get('duration_ms'):.0f}ms)",
            })
        if not same_easing:
            issues.append({
                "reference": r.get("id"),
                "problem": "curva divergente",
                "hint": f"Usar easing {r.get('easing')} ({r.get('easing_css')}), "
                        f"gerado usa {best.get('easing')}",
            })

    score = sum(1 for m in matches if m["ok"]) / len(ref) if ref else 1.0
    return {"score": round(score, 3), "matches": matches, "issues": issues,
            "extra_in_generated": len(unused)}


def compare_structure(ref: dict, gen: dict) -> dict:
    """Compara os tipos de componentes presentes."""
    r = ref.get("component_types", {}) or {}
    g = gen.get("component_types", {}) or {}
    missing = [k for k in r if k not in g]
    extra = [k for k in g if k not in r]
    shared = [k for k in r if k in g]
    score = len(shared) / len(r) if r else 1.0
    issues = []
    for m in missing:
        issues.append({"type": m, "problem": "ausente na versao gerada",
                       "hint": f"Adicionar componente do tipo '{m}'"})
    return {"score": round(score, 3), "missing": missing, "extra": extra,
            "shared": shared, "issues": issues}


def compare(reference: dict, generated: dict) -> dict:
    """Comparacao completa entre referencia e versao gerada."""
    ds_r = reference.get("design_system", {})
    ds_g = generated.get("design_system", {})

    colors = compare_palettes(ds_r.get("colors", {}), ds_g.get("colors", {}))
    layout = compare_layout(ds_r.get("layout", {}) or {}, ds_g.get("layout", {}) or {})
    anims = compare_animations(reference.get("animations", []), generated.get("animations", []))
    struct = compare_structure(reference.get("components", {}), generated.get("components", {}))

    # Proporcoes da tela: um aspect ratio diferente distorce todo o resto.
    vr, vg = reference.get("video", {}), generated.get("video", {})
    ar_r, ar_g = vr.get("aspect_ratio"), vg.get("aspect_ratio")
    proportion_ok = True
    proportion_note = ""
    if ar_r and ar_g:
        d = abs(ar_r - ar_g) / ar_r
        proportion_ok = d <= 0.05
        proportion_note = (
            f"aspect ratio referencia {ar_r} x gerado {ar_g} ({d * 100:.1f}% de diferenca)"
        )

    weights = {"colors": 0.3, "layout": 0.2, "animations": 0.3, "structure": 0.2}
    overall = (
        colors["score"] * weights["colors"]
        + layout["score"] * weights["layout"]
        + anims["score"] * weights["animations"]
        + struct["score"] * weights["structure"]
    )

    all_issues = (
        [{"area": "cores", **i} for i in colors["missing"]]
        + [{"area": "layout", **i} for i in layout["issues"]]
        + [{"area": "animacao", **i} for i in anims["issues"]]
        + [{"area": "estrutura", **i} for i in struct["issues"]]
    )
    if not proportion_ok:
        all_issues.insert(0, {"area": "proporcao", "problem": "aspect ratio divergente",
                              "hint": proportion_note})

    return {
        "overall_score": round(overall, 3),
        "verdict": _verdict(overall, proportion_ok),
        "proportions": {"ok": proportion_ok, "note": proportion_note},
        "colors": colors,
        "layout": layout,
        "animations": anims,
        "structure": struct,
        "issues": all_issues,
        "issue_count": len(all_issues),
    }


def _verdict(score: float, proportion_ok: bool) -> str:
    if not proportion_ok:
        return "reprovado: proporcoes da tela divergem da referencia"
    if score >= 0.9:
        return "aprovado: fidelidade alta"
    if score >= 0.75:
        return "aprovado com ressalvas: ajustes finos pendentes"
    if score >= 0.5:
        return "reprovado: divergencias relevantes"
    return "reprovado: reconstrucao nao corresponde a referencia"
