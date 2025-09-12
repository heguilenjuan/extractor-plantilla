from typing import Tuple, List, Dict
from .base import IPageExtractor
from .ocr_text import extract_text_blocks_from_page_with_ocr_words, extract_text_from_page_with_ocr


class OCRExtractor(IPageExtractor):
    def can_handle(self, page) -> bool:
        return len(page.get_text("text").strip()) == 0

    def extract(self, page, page_num: int) -> Tuple[str, List[Dict]]:
        text = extract_text_from_page_with_ocr(page, dpi=200, lang="spa+eng")
        blocks = extract_text_blocks_from_page_with_ocr_words(
            page, page_num, dpi=200, lang="spa+eng", min_conf=50)
        return text, blocks
