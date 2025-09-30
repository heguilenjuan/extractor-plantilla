# src/services/applier.py
import re
from typing import Dict, Any, List, Tuple

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
    # pequeño margen para tolerar redondeos
    ax0 -= tol; ay0 -= tol; ax1 += tol; ay1 += tol
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def _block_center(blk: Dict[str, Any]) -> Tuple[float, float]:
    x0, y0, x1, y1 = blk["coordinates"]
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)

def _point_in_rect(px:float, py:float, rect: Tuple[float, float, float, float]):
    x0, y0, x1, y1 = rect
    return (x0 <= px <= x1) and (y0 <= py <= y1)

def _cluster_rows_and_order(blocks: List[Dict[str, Any]], row_tol: float = 14.0) -> List[Dict[str, Any]]:
    """
    Agrupa por filas (|Δy| <= row_tol). Dentro de cada fila ordena por x0. Luego ordena filas por y0.
    """
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

    rows.sort(key=lambda row: row[0]["coordinates"][1])     # y0 de la fila

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.extend(r)
    return out


class TemplateApplier:
    """
    Aplica una plantilla sobre los 'blocks' extraídos del PDF.

    template.meta.renderWidth / renderHeight
    template.boxes:  [{id,x,y,w,h,page,...}]
    template.fields: [{key, boxId, regex?, normalizers?, required?, cast?}]

    Blocks del extractor:
      [{page, coordinates:[x0,y0,x1,y1], text, page_width?, page_height?, ...}] en coords PDF.
    """

    def apply(self, template, pdf_text_blocks: List[Dict[str, Any]], *, include_debug: bool = False) -> Dict[str, Any]:
        meta = template.meta or {}
        render_w = float(meta.get("renderWidth") or 600.0)
        render_h = float(meta.get("renderHeight") or 800.0)

        def as_dict(x): return x if isinstance(x, dict) else x.model_dump()
        boxes  = [as_dict(b) for b in (template.boxes or [])]
        fields = [as_dict(f) for f in (template.fields or [])]

        # Agrupar por página y obtener tamaño real si viene en cada block
        by_page: Dict[int, List[Dict[str, Any]]] = {}
        page_size: Dict[int, Tuple[float, float]] = {}  # (pw, ph)

        for blk in pdf_text_blocks:
            p = int(blk.get("page", 1))
            by_page.setdefault(p, []).append(blk)
            pw = blk.get("page_width"); ph = blk.get("page_height")
            if pw and ph:
                page_size[p] = (float(pw), float(ph))

        # Fallback por si faltan pw/ph
        for p, blks in by_page.items():
            if p not in page_size:
                max_x = max((b["coordinates"][2] for b in blks), default=render_w)
                max_y = max((b["coordinates"][3] for b in blks), default=render_h)
                page_size[p] = (max(max_x, render_w), max(max_y, render_h))

        box_text_cache: Dict[str, str] = {}
        debug_boxes: Dict[str, Any] = {} if include_debug else None

        # 1) Texto por box: escalar rect y tomar cualquier bloque que INTERSEQUE
        for b in boxes:
            page = int(b.get("page", 1))
            pw, ph = page_size.get(page, (render_w, render_h))
            sx, sy = (pw / render_w), (ph / render_h)

            x0 = b["x"] * sx
            y0 = b["y"] * sy
            x1 = x0 + b["w"] * sx
            y1 = y0 + b["h"] * sy
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
                debug_boxes[b["id"]] = {
                    "box_name": b.get("name"),
                    "page": page,
                    "rect_pdf": rect,
                    "blocks_count": len(inside),
                    "text_preview": text[:300]
                }

        # 2) Campos
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
                    pass

            if f.get("required") and not val:
                missing_required.append(key)

            out[key] = val

        result: Dict[str, Any] = {"values": out, "missing_required": missing_required}
        if include_debug:
            result["debug"] = {"boxes": debug_boxes}
        return result