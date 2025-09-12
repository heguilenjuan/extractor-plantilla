# src/services/extractors/ocr_text.py
import io
import os
import subprocess
from typing import Dict, List

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

def extract_text_from_page_with_ocr(page: "fitz.Page", dpi: int = 300, lang: str = "spa+eng") -> str:
    img = _page_to_pil(page, dpi=dpi, mode="L")
    return (pytesseract.image_to_string(img, lang=lang, config="--oem 3 --psm 6") or "").strip()

def extract_text_blocks_from_page_with_ocr_words(
    page: "fitz.Page",
    page_num: int,
    dpi: int = 300,
    lang: str = "spa+eng",
    min_conf: int = 50,
) -> List[Dict]:
    """
    Devuelve bloques POR PALABRA con el mismo shape que nativo:
    { page, block_number, coordinates (puntos PDF), text, type, flags }
    """
    scale = dpi / 72.0
    img = _page_to_pil(page, dpi=dpi, mode="L")

    data = pytesseract.image_to_data(
        img,
        output_type=pytesseract.Output.DICT,
        lang=lang,
        config="--oem 3 --psm 6",
    )

    words  = data.get("text", [])
    confs  = data.get("conf", [])
    lefts  = data.get("left", [])
    tops   = data.get("top", [])
    widths = data.get("width", [])
    heights= data.get("height", [])

    all_blocks: List[Dict] = []
    block_no = 0
    n = len(words)

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

        # bbox en píxeles
        x0_px = int(lefts[i]);  y0_px = int(tops[i])
        x1_px = x0_px + int(widths[i])
        y1_px = y0_px + int(heights[i])

        # a puntos PDF
        x0, y0 = x0_px / scale, y0_px / scale
        x1, y1 = x1_px / scale, y1_px / scale

        all_blocks.append({
            "page": page_num,
            "block_number": block_no,
            "coordinates": (x0, y0, x1, y1),
            "text": w,
            "type": 0,
            "flags": 0,
        })
        block_no += 1

    return all_blocks

# helpers
def _page_to_pil(page: "fitz.Page", dpi: int = 300, mode: str = "L") -> Image.Image:
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat)
    return Image.open(io.BytesIO(pix.tobytes("ppm"))).convert(mode)
