# services/page_extractor.py
from typing import Dict, List
from .extractors.base import IPageExtractor

class PageExtractor:
    """
    Coordina estrategias de extracción para una página concreta.
    Aplica la primera estrategia cuya condición `can_handle(page)` sea True.
    Si ninguna la puede manejar, usa la última como fallback (típicamente OCR).

    Retorna un dict por página con:
      {
        "page": int,    
        "page_number": int,
        "origin": "top-left",
        "rotation": int,
        "strategy_used": "native_text" | "ocr" | <otro>,
        "page_width": float,
        "page_height": float,
        "text": str,
        "character_count": int,
        "has_images": bool,
        "blocks": [  # cada block incluye page/page_size y coords en top-left
          {
            "page": int,
            "page_width": float,
            "page_height": float,
            "coordinates": [x0, y0, x1, y1],
            "text": str
          },
          ...
        ],
        "error": str | None
      }
    """

    def __init__(self, strategies: List[IPageExtractor]):
        if not strategies:
            raise ValueError("Se requiere al menos una estrategia de extracción.")
        self._strategies = strategies

    def extract(self, page, page_num: int) -> Dict:
        pw = float(page.rect.width)
        ph = float(page.rect.height)
        rotation = int(getattr(page, "rotation", 0))

        result = {
            "page": page_num,                
            "page_number": page_num,
            "origin": "top-left",            
            "rotation": rotation,            
            "strategy_used": None,
            "page_width": pw,
            "page_height": ph,
            "text": "",
            "character_count": 0,
            "has_images": bool(len(page.get_images()) > 0),
            "blocks": [],
            "error": None,
        }

        try:
            extractor = self._select_strategy(page)
            text, blocks = extractor.extract(page, page_num)

            patched_blocks = []
            for b in (blocks or []):
                b = dict(b)
                # asegurar consistencia
                b["page"] = page_num
                b["page_width"]  = float(b.get("page_width", pw))
                b["page_height"] = float(b.get("page_height", ph))

                # coords como lista de floats
                coords = b.get("coordinates", [0, 0, 0, 0])
                x0, y0, x1, y1 = [float(c) for c in coords]
                # Si alguna estrategia devolviera bottom-left, conviértela allí.
                # Aquí asumimos top-left (fitz nativo).
                b["coordinates"] = [x0, y0, x1, y1]

                patched_blocks.append(b)

            result["text"] = text or ""
            result["character_count"] = len(result["text"])
            result["blocks"] = patched_blocks
            result["strategy_used"] = self._strategy_name(extractor)

        except Exception as e:
            result["error"] = str(e)
        return result

    # -------------------- helpers --------------------

    def _select_strategy(self, page) -> IPageExtractor:
        for s in self._strategies:
            try:
                if s.can_handle(page):
                    return s
            except Exception:
                continue
        return self._strategies[-1]

    def _strategy_name(self, extractor: IPageExtractor) -> str:
        name = extractor.__class__.__name__.lower()
        if "native" in name:
            return "native_text"
        if "ocr" in name:
            return "ocr"
        return name
