# src/services/extractors/combined.py
from typing import Tuple, List, Dict, Optional
from .base import IPageExtractor
from .native_text import extract_text_from_page, extract_text_blocks_from_page
from .ocr_text import (
    extract_text_from_page_with_ocr,
    extract_text_blocks_from_page_with_ocr_words_and_lines,
)

def _norm_native_blocks(blocks: List[Dict], page_num: int, pw: float, ph: float) -> List[Dict]:
    res: List[Dict] = []
    for b in blocks or []:
        nb = {
            "page": page_num,
            "coordinates": [float(c) for c in b.get("coordinates", [0,0,0,0])],
            "text": b.get("text", ""),
            "page_width": float(pw),
            "page_height": float(ph),
            "source": "native",
            "kind": "block",
            "conf": None,
        }
        res.append(nb)
    return res

def _norm_ocr_blocks(blocks: List[Dict], page_num: int, pw: float, ph: float) -> List[Dict]:
    res: List[Dict] = []
    for b in blocks or []:
        nb = {
            "page": page_num,
            "coordinates": [float(c) for c in b.get("coordinates", [0,0,0,0])],
            "text": b.get("text", ""),
            "page_width": float(pw),
            "page_height": float(ph),
            "source": "ocr",
            "kind": b.get("kind", "line"),
            "conf": b.get("conf", None),
        }
        res.append(nb)
    return res

def _iou(a, b):
    ax0, ay0, ax1, ay1 = a; bx0, by0, bx1, by1 = b
    iw = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    ih = max(0.0, min(ay1, by1) - max(ay0, by0))
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max((ax1-ax0)*(ay1-ay0), 1e-6)
    area_b = max((bx1-bx0)*(by1-by0), 1e-6)
    return inter / max(area_a + area_b - inter, 1e-6)

def _norm_text(s: str) -> str:
    return (s or "").strip().replace(" ", "").replace("\n", "")

def _merge_dedupe(native_blocks: List[Dict], ocr_blocks: List[Dict], iou_thr=0.7) -> List[Dict]:
    """Mantiene nativos; agrega OCR si aporta algo en caja distinta."""
    merged: List[Dict] = list(native_blocks)
    for ob in ocr_blocks:
        ob_norm = _norm_text(ob.get("text", ""))
        dup = False
        for nb in merged:
            if _iou(ob["coordinates"], nb["coordinates"]) >= iou_thr:
                if _norm_text(nb.get("text", "")) == ob_norm or len(ob_norm) <= 2:
                    dup = True
                    break
        if not dup:
            merged.append(ob)
    return merged

class CombinedExtractor(IPageExtractor):
    """
    Corre Nativo y OCR, normaliza y une resultados en un esquema unificado.
    - ocr_always=True: siempre ejecuta OCR (recomendado para robustez).
    - Si ocr_always=False: ejecuta OCR sólo si el texto nativo es pobre (< ocr_min_native_chars).
    """
    def __init__(self, ocr_always: bool = True, ocr_min_native_chars: int = 0, dpi=300, lang="spa+eng", min_conf=40):
        self.ocr_always = ocr_always
        self.ocr_min_native_chars = ocr_min_native_chars
        self.dpi = dpi
        self.lang = lang
        self.min_conf = min_conf

    def can_handle(self, page) -> bool:
        return True

    def extract(self, page, page_num: int) -> Tuple[str, List[Dict]]:
        pw, ph = float(page.rect.width), float(page.rect.height)

        # Nativo
        text_nat = extract_text_from_page(page)
        blocks_nat_raw = extract_text_blocks_from_page(page, page_num)
        blocks_nat = _norm_native_blocks(blocks_nat_raw, page_num, pw, ph)

        # OCR condicional
        do_ocr = self.ocr_always or (len((text_nat or "").strip()) < self.ocr_min_native_chars)
        text_ocr, blocks_ocr = "", []
        if do_ocr:
            text_ocr = extract_text_from_page_with_ocr(page, dpi=self.dpi, lang=self.lang)
            blocks_ocr_raw = extract_text_blocks_from_page_with_ocr_words_and_lines(
                page, page_num, dpi=self.dpi, lang=self.lang, min_conf=self.min_conf
            )
            blocks_ocr = _norm_ocr_blocks(blocks_ocr_raw, page_num, pw, ph)

        # Merge
        blocks = _merge_dedupe(blocks_nat, blocks_ocr, iou_thr=0.7)

        # Texto combinado
        combined_text = (text_nat or "").strip()
        if text_ocr:
            nt = _norm_text(text_nat)
            ot = _norm_text(text_ocr)
            if ot and ot not in nt:
                combined_text = (combined_text + "\n\n" + text_ocr).strip()

        return combined_text, blocks
