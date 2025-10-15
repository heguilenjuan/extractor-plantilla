import re
import unicodedata
from typing import List, Dict, Optional, Tuple

# =========================================
# Números (tolerante a miles con . o espacio y decimales con , o .)
#  - 50.526.960,00
#  - 50,526,960.00
#  - 110 966 882,11
# =========================================
NUM_RE = re.compile(r"(?:\d{1,3}(?:[.\s]\d{3})+|\d+)(?:[.,]\d{2})?")

def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s or "")
        if unicodedata.category(c) != "Mn"
    )

def _norm_text(s: str) -> str:
    s = (s or "").replace("\xa0", " ").replace("\n", " ").replace("\r", " ")
    s = _strip_accents(s).lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s

def _extract_number(s: str) -> Optional[str]:
    """Devuelve SOLO el número detectado dentro del texto (o None)."""
    if not s:
        return None
    m = NUM_RE.search(_norm_text(s))
    return m.group(0) if m else None

def _center_y(b: Dict) -> float:
    x0,y0,x1,y1 = b["coordinates"]
    return (y0+y1)/2.0

# -----------------------------
# Tokens por proveedor (tolerantes a OCR)
# -----------------------------
LABEL_TOKENS_GUERRINI = {
    "SUBTOTAL": [["subtotal"]],
    "IVA_21":   [["iva","21"]],
    "PERCEP":   [["percep","iibb"]],
    "TOTAL":    [["total"]],
}

LABEL_TOKENS_PIRELLI = {
    "SUBTOTAL": [["subtotal"], ["imp","neto"]],
    "IVA_21":   [["iva","21"]],
    "PERCEP":   [["perc","rg","3337"], ["percep","iibb"]],
    "TOTAL":    [["importe","total"], ["total"]],
}

LABEL_TOKENS_GENERIC = {
    "SUBTOTAL": [["subtotal"], ["imp","neto"]],
    "IVA_21":   [["iva","21"]],
    "PERCEP":   [["perc","rg","3337"], ["percep","iibb"]],
    "TOTAL":    [["importe","total"], ["total"]],
}

def get_label_tokens_for_proveedor(proveedor: Optional[str]) -> Dict[str, List[List[str]]]:
    if not proveedor:
        return LABEL_TOKENS_GENERIC
    p = proveedor.lower().strip()
    if "pirelli" in p:
        return LABEL_TOKENS_PIRELLI
    if "guerrini" in p:
        return LABEL_TOKENS_GUERRINI
    return LABEL_TOKENS_GENERIC

def _text_has_all_tokens(t: str, tokens: List[str]) -> bool:
    return all(tok in t for tok in tokens)

def _is_label(text: str, token_options: List[List[str]]) -> bool:
    nt = _norm_text(text)
    return any(_text_has_all_tokens(nt, opt) for opt in token_options)

def _has_any_label_tokens(text: str) -> bool:
    """Para filtrar candidatos que todavía contienen 'perc', 'iibb', 'iva', 'neto', etc."""
    nt = _norm_text(text)
    noisy = ("perc", "percep", "iibb", "rg", "iva", "neto", "importe", "total", "subtotal")
    return any(tok in nt for tok in noisy)

# -----------------------------
# IN-LINE: valor en el mismo bloque del label
# -----------------------------
def _find_value_inline(lab_text: str) -> Optional[str]:
    # Busca el primer número luego del label en el mismo bloque.
    return _extract_number(lab_text)

# -----------------------------
# DERECHA y DEBAJO
# -----------------------------
def _find_value_right(
    blocks: List[Dict], lab: Dict, *, x_min_gap: float, y_tol: float
) -> Optional[str]:
    lx0, ly0, lx1, ly1 = lab["coordinates"]
    lcy = (ly0 + ly1)/2.0
    candidates = []
    for b in blocks:
        x0,y0,x1,y1 = b["coordinates"]
        if x0 <= lx1 + x_min_gap:
            continue
        cy = (y0+y1)/2.0
        num = _extract_number(b.get("text",""))
        if not num:
            continue
        # Evitar bloques que mezclan otros labels (para no traer "perc. rg ... 2.684.682,63")
        if _has_any_label_tokens(b.get("text","")):
            continue
        if abs(cy - lcy) <= y_tol:
            dist = (x0 - lx1) + abs(cy - lcy) * 0.5
            candidates.append((dist, num))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0])
    return candidates[0][1]

def _find_value_below(
    blocks: List[Dict], lab: Dict, *, y_min_gap: float, x_overlap_tol: float
) -> Optional[str]:
    lx0, ly0, lx1, ly1 = lab["coordinates"]
    candidates = []
    for b in blocks:
        x0,y0,x1,y1 = b["coordinates"]
        if y0 <= ly1 + y_min_gap:
            continue  # debe estar debajo
        num = _extract_number(b.get("text",""))
        if not num:
            continue
        if _has_any_label_tokens(b.get("text","")):
            continue
        # Solape horizontal con el label
        overlap = max(0, min(lx1, x1) - max(lx0, x0))
        width_lab = max(1.0, (lx1 - lx0))
        overlap_ratio = overlap / width_lab
        if overlap_ratio >= x_overlap_tol:
            dist = (y0 - ly1) + abs((x0+x1)/2 - (lx0+lx1)/2) * 0.05
            candidates.append((dist, num))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0])
    return candidates[0][1]

def _candidate_labels(blocks: List[Dict], token_options: List[List[str]]) -> List[Dict]:
    return [b for b in blocks if _is_label(b.get("text",""), token_options)]

def find_value_near_label(
    blocks: List[Dict],
    token_options: List[List[str]],
    *,
    x_min_gap: float = 6.0,
    y_tolerance: float = 22.0,
    y_min_gap_below: float = 4.0,
    x_overlap_tol_below: float = 0.25
) -> Optional[str]:
    labels = _candidate_labels(blocks, token_options)
    if not labels:
        return None
    labels.sort(key=lambda b: (round(b["coordinates"][1],1), b["coordinates"][0]))
    lab = labels[0]
    lab_text = lab.get("text","")

    # 1) inline
    inline_num = _find_value_inline(lab_text)
    if inline_num:
        return inline_num

    # 2) derecha
    right_num = _find_value_right(blocks, lab, x_min_gap=x_min_gap, y_tol=y_tolerance)
    if right_num:
        return right_num

    # 3) debajo
    below_num = _find_value_below(blocks, lab, y_min_gap=y_min_gap_below, x_overlap_tol=x_overlap_tol_below)
    if below_num:
        return below_num

    return None

# API principal
def extract_totals(
    blocks: List[Dict],
    proveedor: Optional[str] = None,
    *,
    x_min_gap: float = 6.0,
    y_tolerance: float = 22.0
) -> Dict[str, Optional[str]]:
    tokens = get_label_tokens_for_proveedor(proveedor)
    out: Dict[str, Optional[str]] = {}
    for key, token_opts in tokens.items():
        out[key] = find_value_near_label(
            blocks,
            token_opts,
            x_min_gap=x_min_gap,
            y_tolerance=y_tolerance,
            y_min_gap_below=4.0,
            x_overlap_tol_below=0.25
        )
    return out

def infer_proveedor_from_template_id(plantilla_id: Optional[str]) -> Optional[str]:
    if not plantilla_id:
        return None
    parts = str(plantilla_id).split("-")
    if parts:
        cand = parts[-1].strip().lower()
        if cand and cand not in {"template", "tpl"}:
            return cand
    return None
