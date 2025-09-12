from typing import Tuple, List, Dict
from .base import IPageExtractor
from .native_text import extract_text_from_page, extract_text_blocks_from_page

class NativeExtractor(IPageExtractor):
    """Estrategia para páginas con texto nativo (PyMuPDF)."""

    def can_handle(self, page) -> bool:
        # Si la página devuelve algo de texto -> es nativa
        txt = page.get_text("text").strip()
        return len(txt) > 0

    def extract(self, page, page_num: int) -> Tuple[str, List[Dict]]:
        text = extract_text_from_page(page)
        blocks = extract_text_blocks_from_page(page, page_num)
        return text, blocks
