class StatsAggregator:
    """Acumula metricas de extracion a nivel PDF."""
    def __init__(self):
        self._native_pages = 0
        self._ocr_pages = 0
        self._total_chars = 0

    def add(self, strategy_used: str, character_count: int) -> None:
        """Suma metricas de una pagina procesada."""
        if strategy_used == "native_text":
            self._native_pages += 1
        else:
            self._ocr_pages += 1
        self._total_chars += int(character_count or 0)

    def to_dict(self) -> dict:
        """Devuelve el snapshot de la metricas acumuladas"""
        return {
            "native_text_pages": self._native_pages,
            "ocr_pages": self._ocr_pages,
            "total_characters": self._total_chars,
        }
