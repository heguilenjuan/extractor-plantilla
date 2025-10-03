# src/services/extractors/ocr.py
from typing import Tuple, List, Dict
from .base import IPageExtractor
from .ocr_text import extract_text_from_page_with_ocr, extract_text_blocks_from_page_with_ocr_words_and_lines

class OCRExtractor(IPageExtractor):
    def can_handle(self, page) -> bool:
        # Si no hay texto nativo => usamos OCR
        return len(page.get_text("text").strip()) == 0

    def extract(self, page, page_num: int) -> Tuple[str, List[Dict]]:
        # Podés subir a 300 DPI si necesitás precisión (+lento)
        text = extract_text_from_page_with_ocr(page, dpi=200, lang="spa+eng")
        blocks = extract_text_blocks_from_page_with_ocr_words_and_lines(
            page, page_num, dpi=200, lang="spa+eng", min_conf=50
        )
        return text, blocks
