import fitz
from typing import Dict, Any, List
from .pageExtractor import PageExtractor
from .statsAgregator import StatsAggregator


class PdfProcessor:
    """Encargado de procesar el PDF completo"""

    def __init__(self, page_extractor: PageExtractor):
        self.page_extractor = page_extractor

    def process(self, file_path: str) -> Dict[str, Any]:
        """Procesa unn PDF y devuelve un resultado estructurado"""

        results = {
            "total_pages": 0,
            "pages": [],
            "extraction_stats": {
                "native_text_pages": 0,
                "ocr_pages": 0,
                "total_characters": 0,
            }
        }

        stats = StatsAggregator()

        try:
            with fitz.open(file_path) as doc:
                results["total_pages"] = len(doc)

                for page_num, page in enumerate(doc, start=1):
                    page_result = self.page_extractor.extract(page, page_num)

                # Guarda el resultado
                results["pages"].append(page_result)
                # Actualiza estadisticas
                stats.add(page_result["strategy_used"],
                          page_result["character_count"])
            # Agrega los stats acumulados
            results["extraction_stats"].update(stats.to_dict())
            return results
        
        except Exception as e:
            raise Exception(f"Error procesando PDF: {str(e)}")