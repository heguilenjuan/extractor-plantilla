import re
from typing import Dict, Any, List, Tuple, Optional
from .geometry import rect_intersects
from .transforms import to_pdf_scale_from_meta


def compile_anchor_pattern(anchor: Dict[str, Any]) -> re.Pattern:
    """Compila el patron de un anchor"""
    pat = anchor.get("pattern") or ""
    kind = (anchor.get("kind") or "regex").lower()
    flags = re.MULTILINE | re.DOTALL

    if not anchor.get("caseSensitive"):
        flags |= re.IGNORECASE
    if kind == "text":
        pat = re.escape(pat)

    return re.compile(pat, flags)


def find_anchor_Q(anchor: Dict[str, Any], page_blocks: List[Dict[str, Any]], page_meta: Dict[str, Any]) -> Optional[Tuple[float, float, Dict[str, Any]]]:
    """Encuentra un anchor en los bloques de pagina. Devuelve (u, v, block) o None si no se encuentra"""
    if not anchor.get("pattern"):
        return None

    scale = to_pdf_scale_from_meta(page_meta)

    # Calcular rectangulo de busqueda
    sb = anchor.get("searchBox") or {
        "x": anchor["x"] - 50, "y": anchor["y"] - 20, "w": 100, "h": 40
    }
    rx0 = float(sb["x"]) * scale
    ry0 = float(sb["y"]) * scale
    rx1 = (float(sb["x"]) + float(sb["w"])) * scale
    ry1 = (float(sb["y"]) + float(sb["h"])) * scale
    search_rect = (rx0, ry0, rx1, ry1)

    pattern = compile_anchor_pattern(anchor)
    candidates = []

    for block in page_blocks:
        x0, y0, x1, y1 = block["coordinates"]
        if rect_intersects(search_rect, (x0, y0, x1, y1), tol=0.5):
            text = block.get("text", "")
            if pattern.search(text):
                candidates.append(block)

    if not candidates:
        return None

    # Encotnrar el mas cercano al punto esperado
    exp_u = float(anchor["x"]) * scale
    exp_v = float(anchor["y"]) * scale

    def distance_squared(block):
        x0, y0, _, _ = block["coordinates"]
        dx = (x0 - exp_u)
        dy = (y0 - exp_v)
        return dx * dx + dy * dy

    best_block = min(candidates, key=distance_squared)
    u, v = best_block["coordinates"][0], best_block["coordinates"][1]

    return (u, v, best_block)
