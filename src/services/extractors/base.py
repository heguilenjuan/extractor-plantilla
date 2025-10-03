#extractors/base

from typing import Tuple, List, Dict, Protocol, runtime_checkable

@runtime_checkable
class IPageExtractor(Protocol):
    """Contrato para estrategias de extracción de una página PDF."""

    def can_handle(self, page) -> bool:
        """Indica si esta estrategia puede manejar la página."""
        ...

    def extract(self, page, page_num: int) -> Tuple[str, List[Dict]]:
        """
        Extrae texto (y opcionalmente bloques) de la página.
        Retorna: (text, blocks)
        - text: str con el texto plano
        - blocks: lista de bloques enriquecidos (puede ser [])
        """
        ...
