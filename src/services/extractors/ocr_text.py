# src/services/extractors/ocr_text.py (patched to include 'conf' per word)
import io
import os
import subprocess
from typing import Dict, List, Tuple
import fitz
import pytesseract
from PIL import Image

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
else:
    try:
        out = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, timeout=5)
        if out.returncode != 0:
            print("❌ ADVERTENCIA: Tesseract no encontrado. Ajusta TESSERACT_PATH o agrega al PATH.")
    except Exception:
        print("❌ ADVERTENCIA: Tesseract no encontrado. Ajusta TESSERACT_PATH o agrega al PATH.")

def _page_to_pil(page: "fitz.Page", dpi: int = 300, mode: str = "L") -> Image.Image:
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat)
    return Image.open(io.BytesIO(pix.tobytes("ppm"))).convert(mode)

def extract_text_from_page_with_ocr(page: "fitz.Page", dpi: int = 300, lang: str = "spa+eng") -> str:
    img = _page_to_pil(page, dpi=dpi, mode="L")
    return (pytesseract.image_to_string(img, lang=lang, config="--oem 3 --psm 6") or "").strip()

def _to_pdf_rect(ix0:int, iy0:int, iw:int, ih:int, scale:float) -> Tuple[float,float,float,float]:
    x0 = ix0 / scale; y0 = iy0 / scale
    x1 = (ix0 + iw) / scale; y1 = (iy0 + ih) / scale
    return float(x0), float(y0), float(x1), float(y1)

def extract_text_blocks_from_page_with_ocr_words_and_lines(
    page: "fitz.Page",
    page_num: int,
    dpi: int = 300,
    lang: str = "spa+eng",
    min_conf: int = 40,
) -> List[Dict]:
    """
    Devuelve bloques de LINEA (primero) y de PALABRA (después)
    Cada block: { page, block_number, coordinates:[x0,y0,x1,y1], text, type:0, flags:0, kind:"line"|"word", conf: int|None }
    """
    scale = dpi / 72.0
    img = _page_to_pil(page, dpi=dpi, mode="L")

    data = pytesseract.image_to_data(
        img,
        output_type=pytesseract.Output.DICT,
        lang=lang,
        config="--oem 3 --psm 6",
    )

    words   = data.get("text", [])
    confs   = data.get("conf", [])
    lefts   = data.get("left", [])
    tops    = data.get("top", [])
    widths  = data.get("width", [])
    heights = data.get("height", [])
    bnums   = data.get("block_num", [])
    pnums   = data.get("par_num", [])
    lnums   = data.get("line_num", [])
    n = len(words)

    line_groups: Dict[Tuple[int,int,int], List[int]] = {}
    word_blocks: List[Dict] = []
    next_id = 0

    for i in range(n):
        w = (words[i] or "").strip()
        if not w:
            continue
        try:
            c = int(float(confs[i]))
        except Exception:
            c = -1
        if c < min_conf:
            continue

        ix0 = int(lefts[i]); iy0 = int(tops[i])
        iw  = int(widths[i]); ih = int(heights[i])

        x0, y0, x1, y1 = _to_pdf_rect(ix0, iy0, iw, ih, scale)

        word_blocks.append({
            "page": page_num,
            "block_number": next_id,
            "coordinates": [x0, y0, x1, y1],
            "text": w,
            "type": 0,
            "flags": 0,
            "kind": "word",
            "conf": c,
        })
        next_id += 1

        key = (int(bnums[i]), int(pnums[i]), int(lnums[i]))
        line_groups.setdefault(key, []).append(len(word_blocks) - 1)

    line_blocks: List[Dict] = []
    for key, idxs in line_groups.items():
        if not idxs:
            continue
        xs0 = []; ys0 = []; xs1 = []; ys1 = []; parts = []; confs_line = []
        for wi in idxs:
            wb = word_blocks[wi]
            x0, y0, x1, y1 = wb["coordinates"]
            xs0.append(x0); ys0.append(y0); xs1.append(x1); ys1.append(y1)
            parts.append(wb["text"])
            if wb.get("conf") is not None:
                confs_line.append(wb["conf"])
        lx0, ly0, lx1, ly1 = min(xs0), min(ys0), max(xs1), max(ys1)
        text_line = " ".join(parts).strip()
        if not text_line:
            continue
        avg_conf = int(sum(confs_line)/len(confs_line)) if confs_line else None
        line_blocks.append({
            "page": page_num,
            "block_number": next_id,
            "coordinates": [float(lx0), float(ly0), float(lx1), float(ly1)],
            "text": text_line,
            "type": 0,
            "flags": 0,
            "kind": "line",
            "conf": avg_conf,
        })
        next_id += 1

    return line_blocks + word_blocks
