# services/page_extractor.py
from typing import Dict, List, Optional
from .extractors.base import IPageExtractor

class PageExtractor:
    """
    Coordina estrategias de extracción para una página concreta.
    Aplica la primera estrategia cuya condición `can_handle(page)` sea True.
    Si ninguna la puede manejar, usa la última como fallback (típicamente OCR).
    """

    def __init__(self, strategies: List[IPageExtractor]):
        if not strategies:
            raise ValueError("Se requiere al menos una estrategia de extracción.")
        self._strategies = strategies

    def extract(self, page, page_num: int) -> Dict:
        """
        Retorna un resultado estructurado de la página:

        {
          "page_number": int,
          "strategy_used": "native_text" | "ocr" | <otro>,
          "text": str,
          "character_count": int,
          "has_images": bool,
          "blocks": List[Dict],     # solo para nativo (puede ser [])
          "error": str | None
        }
        """
        result = {
            "page_number": page_num,
            "strategy_used": None,
            "text": "",
            "character_count": 0,
            "has_images": bool(len(page.get_images()) > 0),
            "blocks": [],
            "error": None,
        }

        try:
            extractor = self._select_strategy(page)
            text, blocks = extractor.extract(page, page_num)

            result["text"] = text or ""
            result["character_count"] = len(result["text"])
            result["blocks"] = blocks or []
            result["strategy_used"] = self._strategy_name(extractor)

        except Exception as e:
            # No interrumpimos el procesamiento del PDF completo;
            # devolvemos el error a nivel de página.
            result["error"] = str(e)

        return result

    # -------------------- helpers --------------------

    def _select_strategy(self, page) -> IPageExtractor:
        """Devuelve la primera estrategia que 'puede' manejar la página; si no, fallback a la última."""
        for s in self._strategies:
            try:
                if s.can_handle(page):
                    return s
            except Exception:
                continue
        return self._strategies[-1]

    def _strategy_name(self, extractor: IPageExtractor) -> str:
        """Nombre legible/estable para la estrategia usada."""
        name = extractor.__class__.__name__.lower()
        if "native" in name:
            return "native_text"
        if "ocr" in name:
            return "ocr"
        return name  
