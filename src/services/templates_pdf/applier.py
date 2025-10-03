# src/services/applier.py
import re
from typing import Dict, Any, List, Tuple, Optional
import math

import numpy as np  # pip install numpy

# Normalizadores disponibles
NORMALIZERS = {
    "trim": lambda s: s.strip(),
    "toUpper": lambda s: s.upper(),
    "toLower": lambda s: s.lower(),
    "removeSpaces": lambda s: s.replace(" ", ""),
    "keepDigits": lambda s: "".join(ch for ch in s if ch.isdigit()),
}

def _apply_normalizers(text: str, norms: List[str] | None) -> str:
    s = text or ""
    for n in norms or []:
        fn = NORMALIZERS.get(n)
        if fn:
            s = fn(s)
    return s

def _rect_intersects(a: Tuple[float,float,float,float], b: Tuple[float,float,float,float], tol: float = 0.5) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ax0 -= tol; ay0 -= tol; ax1 += tol; ay1 += tol
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)

def _cluster_rows_and_order(blocks: List[Dict[str, Any]], row_tol: float = 14.0) -> List[Dict[str, Any]]:
    if not blocks:
        return []
    bs = sorted(blocks, key=lambda b: b["coordinates"][1])  # y0
    rows: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = [bs[0]]
    base_y = bs[0]["coordinates"][1]
    for b in bs[1:]:
        y0 = b["coordinates"][1]
        if abs(y0 - base_y) <= row_tol:
            current.append(b)
        else:
            current.sort(key=lambda k: k["coordinates"][0])  # x0
            rows.append(current)
            current = [b]
            base_y = y0
    current.sort(key=lambda k: k["coordinates"][0])
    rows.append(current)
    rows.sort(key=lambda row: row[0]["coordinates"][1])
    out: List[Dict[str, Any]] = []
    for r in rows: out.extend(r)
    return out

# ---------- Utils de transformaciones ----------

def _to_pdf_scale_from_meta(page_meta: Dict[str, Any]) -> float:
    """factor para ir de coordenadas de plantilla (renderWidth) a coords PDF base."""
    rw = float(page_meta.get("renderWidth") or 600.0)
    pw = float(page_meta.get("pdfWidthBase") or rw)
    # viewportScale = rw / pdfWidthBase (si lo calculaste así); pero por seguridad:
    return pw / rw

def _rect_xywh_to_xyxy(x: float, y: float, w: float, h: float) -> Tuple[float,float,float,float]:
    return (x, y, x + w, y + h)

def _apply_affine(T: np.ndarray, x: float, y: float) -> Tuple[float, float]:
    # T: 2x3
    X = np.array([x, y, 1.0], dtype=float)
    u, v = (T @ X)
    return float(u), float(v)

def _fit_affine(src: List[Tuple[float,float]], dst: List[Tuple[float,float]]) -> np.ndarray:
    """Devuelve matriz 2x3 de la transformación afín que aproxima src->dst (mínimos cuadrados)."""
    n = len(src)
    A = np.zeros((2*n, 6), dtype=float)
    b = np.zeros((2*n,), dtype=float)
    for i, ((x, y), (u, v)) in enumerate(zip(src, dst)):
        A[2*i,   :] = [x, y, 1, 0, 0, 0]
        A[2*i+1, :] = [0, 0, 0, x, y, 1]
        b[2*i]   = u
        b[2*i+1] = v
    # x = (A^T A)^-1 A^T b  == np.linalg.lstsq
    params, *_ = np.linalg.lstsq(A, b, rcond=None)
    a, b1, c, d, e, f = params
    T = np.array([[a, b1, c],
                  [d,  e,  f]], dtype=float)
    return T

def _fit_similarity(p1: Tuple[float,float], p2: Tuple[float,float],
                    q1: Tuple[float,float], q2: Tuple[float,float]) -> np.ndarray:
    """Similaridad (escala+rot+traslación) que lleva p1->q1 y p2->q2."""
    # vector en plantilla y en destino
    vx_p = p2[0] - p1[0]; vy_p = p2[1] - p1[1]
    vx_q = q2[0] - q1[0]; vy_q = q2[1] - q1[1]
    # escala = |q|/|p|
    norm_p = math.hypot(vx_p, vy_p) or 1.0
    norm_q = math.hypot(vx_q, vy_q)
    s = norm_q / norm_p
    # ángulo
    ang_p = math.atan2(vy_p, vx_p)
    ang_q = math.atan2(vy_q, vx_q)
    theta = ang_q - ang_p
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    # rot+esc
    a = s * cos_t; b1 = s * (-sin_t)
    d = s * sin_t; e = s * cos_t
    # traslación: q1 = R*s*p1 + t
    c = q1[0] - (a * p1[0] + b1 * p1[1])
    f = q1[1] - (d * p1[0] + e * p1[1])
    return np.array([[a, b1, c],
                     [d, e,  f]], dtype=float)

# ---------- Matching de anclas ----------

def _compile_regex(pat: str, case_sensitive: bool) -> re.Pattern:
    flags = re.MULTILINE | re.DOTALL
    if not case_sensitive:
        flags |= re.IGNORECASE
    return re.compile(pat, flags)

def _find_anchor_Q(anchor: Dict[str, Any], page_blocks: List[Dict[str, Any]],
                   page_meta: Dict[str, Any]) -> Optional[Tuple[float, float, Dict[str, Any]]]:
    """
    Devuelve (u,v, block) donde (u,v) es el punto de referencia del match (topleft del bloque que matchea).
    Busca dentro del searchBox escalado a coordenadas PDF base.
    """
    if not anchor.get("pattern"):
        return None

    s = _to_pdf_scale_from_meta(page_meta)

    # rect de búsqueda en coords de plantilla -> pasar a coords PDF
    sb = anchor.get("searchBox") or {"x": anchor["x"]-50, "y": anchor["y"]-20, "w": 100, "h": 40}
    rx0 = float(sb["x"]) * s
    ry0 = float(sb["y"]) * s
    rx1 = (float(sb["x"]) + float(sb["w"])) * s
    ry1 = (float(sb["y"]) + float(sb["h"])) * s
    search_rect = (rx0, ry0, rx1, ry1)

    pat = _compile_regex(anchor["pattern"], bool(anchor.get("caseSensitive")))
    candidates = []
    for blk in page_blocks:
        x0, y0, x1, y1 = blk["coordinates"]
        if _rect_intersects(search_rect, (x0,y0,x1,y1), tol=0.5):
            txt = blk.get("text", "")
            if pat.search(txt):
                candidates.append(blk)

    if not candidates:
        return None

    # Elegimos el más cercano al punto esperado escalado
    exp_u = float(anchor["x"]) * s
    exp_v = float(anchor["y"]) * s
    def dist2(blk):
        x0, y0, _, _ = blk["coordinates"]
        dx = (x0 - exp_u); dy = (y0 - exp_v)
        return dx*dx + dy*dy
    blk = min(candidates, key=dist2)
    u, v = blk["coordinates"][0], blk["coordinates"][1]  # topleft del bloque
    return (u, v, blk)

def _transform_box(T: np.ndarray, b: Dict[str, Any]) -> Tuple[float,float,float,float]:
    """Transforma el rectángulo (x,y,w,h) de la plantilla a coords PDF usando T (aplica a las 4 esquinas)."""
    x, y, w, h = float(b["x"]), float(b["y"]), float(b["w"]), float(b["h"])
    p = [(x, y), (x+w, y), (x+w, y+h), (x, y+h)]
    q = [ _apply_affine(T, px, py) for (px, py) in p ]
    xs = [u for (u,_) in q]; ys = [v for (_,v) in q]
    return (min(xs), min(ys), max(xs), max(ys))

# ---------- Applier principal ----------

class TemplateApplier:
    """
    Aplica una plantilla sobre los 'blocks' extraídos del PDF.

    Estructura esperada en template.meta:
      meta.pages[page] = {
        pdfWidthBase, pdfHeightBase, renderWidth, renderHeight, viewportScale, rotation, anchors:[...]
      }

    Blocks del extractor:
      [{page, coordinates:[x0,y0,x1,y1], text, page_width?, page_height?, ...}] en coords PDF.
    """

    def apply(self, template, pdf_text_blocks: List[Dict[str, Any]], *, include_debug: bool = False) -> Dict[str, Any]:
        meta = template.meta or {}
        pages_meta: Dict[int, Dict[str, Any]] = {}
        if "pages" in meta:
            # claves pueden venir como str o int
            for k, v in meta["pages"].items():
                pages_meta[int(k)] = v

        def as_dict(x): return x if isinstance(x, dict) else x.model_dump()
        boxes  = [as_dict(b) for b in (template.boxes or [])]
        fields = [as_dict(f) for f in (template.fields or [])]

        # Agrupar blocks por página y tamaños
        by_page: Dict[int, List[Dict[str, Any]]] = {}
        page_size: Dict[int, Tuple[float, float]] = {}  # (pw, ph)
        for blk in pdf_text_blocks:
            p = int(blk.get("page", 1))
            by_page.setdefault(p, []).append(blk)
            pw = blk.get("page_width"); ph = blk.get("page_height")
            if pw and ph:
                page_size[p] = (float(pw), float(ph))
        # Fallback
        for p, blks in by_page.items():
            if p not in page_size:
                max_x = max((b["coordinates"][2] for b in blks), default=600.0)
                max_y = max((b["coordinates"][3] for b in blks), default=800.0)
                page_size[p] = (max_x, max_y)

        # Prepara estructuras de salida
        box_text_cache: Dict[str, str] = {}
        debug: Dict[str, Any] = {} if include_debug else None

        # --- 1) Por página: obtener T con anclas (o fallback) ---
        T_by_page: Dict[int, np.ndarray] = {}
        anchors_debug: Dict[int, Any] = {}

        for p, blks in by_page.items():
            pm = pages_meta.get(p, {})
            # Si no hay meta de página, usamos escala directa (plantilla->pdf) basada en tamaños:
            if not pm:
                rw = float(meta.get("renderWidth") or 600.0)
                pw, ph = page_size[p]
                sx, sy = pw / rw, ph / float(meta.get("renderHeight") or (rw*1.414))
                T = np.array([[sx, 0, 0],
                              [0, sy, 0]], dtype=float)
                T_by_page[p] = T
                continue

            s = _to_pdf_scale_from_meta(pm)

            P: List[Tuple[float,float]] = []  # puntos de plantilla
            Q: List[Tuple[float,float]] = []  # puntos en PDF real
            found = []

            for a in (pm.get("anchors") or []):
                res = _find_anchor_Q(a, blks, pm)
                if res is None:
                    found.append({"id": a.get("id"), "name": a.get("name"), "matched": False})
                    continue
                u, v, blk = res
                P.append( (float(a["x"]), float(a["y"])) )
                Q.append( (u, v) )
                found.append({
                    "id": a.get("id"), "name": a.get("name"),
                    "matched": True, "expected": (float(a["x"])*s, float(a["y"])*s),
                    "found": (u, v), "block": blk
                })

            T: Optional[np.ndarray] = None
            if len(P) >= 3:
                T = _fit_affine(P, Q)
            elif len(P) == 2:
                T = _fit_similarity(P[0], P[1], Q[0], Q[1])
            elif len(P) == 1:
                # 1 ancla: solo traslación + escala conocida (de meta)
                exp_u = P[0][0] * s; exp_v = P[0][1] * s
                du = Q[0][0] - exp_u; dv = Q[0][1] - exp_v
                T = np.array([[s, 0, du],
                              [0, s, dv]], dtype=float)
            else:
                # Sin anclas: fallback a escala meta
                T = np.array([[s, 0, 0],
                              [0, s, 0]], dtype=float)

            T_by_page[p] = T
            if include_debug:
                anchors_debug[p] = {
                    "found": found,
                    "T": T.tolist()
                }

        # --- 2) Texto por box reproyectando con T ---
        for b in boxes:
            page = int(b.get("page", 1))
            T = T_by_page.get(page)
            if T is None:
                # fallback bruto por si algo faltó
                pw, ph = page_size.get(page, (600.0, 800.0))
                rw = float(meta.get("renderWidth") or 600.0)
                rh = float(meta.get("renderHeight") or 800.0)
                sx, sy = pw/rw, ph/rh
                T = np.array([[sx, 0, 0],
                              [0, sy, 0]], dtype=float)

            x0, y0, x1, y1 = _transform_box(T, b)
            rect = (x0, y0, x1, y1)

            page_blocks = by_page.get(page, [])
            inside = [blk for blk in page_blocks if _rect_intersects(rect, tuple(blk["coordinates"]), tol=0.75)]
            if inside:
                inside = _cluster_rows_and_order(inside, row_tol=14.0)
                text = "\n".join(blk.get("text", "") for blk in inside).strip()
            else:
                text = ""

            box_text_cache[b["id"]] = text

            if include_debug:
                debug.setdefault("boxes", {})[b["id"]] = {
                    "box_name": b.get("name"),
                    "page": page,
                    "rect_pdf": rect,
                    "blocks_count": len(inside),
                    "text_preview": text[:300]
                }

        # --- 3) Campos ---
        out: Dict[str, Any] = {}
        missing_required: List[str] = []

        for f in fields:
            key = f["key"]
            box_id = f["boxId"]
            raw = box_text_cache.get(box_id, "") or ""

            val = raw
            pattern = f.get("regex")
            if pattern:
                m = re.search(pattern, raw, flags=re.MULTILINE | re.DOTALL)
                val = (m.group(1) if m and m.groups() else (m.group(0) if m else ""))

            val = _apply_normalizers(val, f.get("normalizers"))

            cast = f.get("cast")
            if cast and val:
                try:
                    if cast == "int":
                        val = int(val.replace(",", "").replace(".", ""))
                    elif cast in ("float", "decimal"):
                        val = float(val.replace(",", ""))
                except Exception:
                    # si falla el cast, devolvemos texto normalizado
                    pass

            if f.get("required") and not val:
                missing_required.append(key)

            out[key] = val

        result: Dict[str, Any] = {
            "values": out,
            "missing_required": missing_required,
        }
        if include_debug:
            result["debug"] = {
                "anchors": anchors_debug,
                "transforms": {p: T_by_page[p].tolist() for p in T_by_page},
            }
        return result
