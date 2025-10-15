# src/services/page_extractor_factory.py
from typing import List
from .pageExtractor import PageExtractor
from .extractors.combined import CombinedExtractor

def build_page_extractor_unified() -> PageExtractor:
    """
    Devuelve un PageExtractor con un único CombinedExtractor
    que corre Nativo + OCR y devuelve salida unificada y consistente.
    """
    strategies = [CombinedExtractor(ocr_always=True, dpi=300, lang="spa+eng", min_conf=40)]
    return PageExtractor(strategies)
