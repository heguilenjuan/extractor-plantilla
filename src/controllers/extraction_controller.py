from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, List

from src.services.uploads import Uploads
from src.services.pdfProcessor import PdfProcessor
from src.services.pageExtractor import PageExtractor
from src.services.extractors.native import NativeExtractor
from src.services.extractors.ocr import OCRExtractor

from src.services.templates_pdf.engine import TemplateEngine
from src.services.templates_pdf.repo import JsonTemplateRepository

router = APIRouter(prefix="/api/v1", tags=["Extraction"])

# -------------------- Dependencias --------------------


def get_uploads() -> Uploads:
    return Uploads()


def get_pdf_processor() -> PdfProcessor:
    page_extractor = PageExtractor([NativeExtractor(), OCRExtractor()])
    return PdfProcessor(page_extractor)


def get_template_engine() -> TemplateEngine:
    # Ajusta la ruta si queres guardar en otro lugar
    repo = JsonTemplateRepository("./data/templates.json")
    return TemplateEngine(repo)

# -------------------- Endpoints --------------------


@router.post("/extract-text")
async def extract_text_from_pdf(
    file: UploadFile = File(...),
    uploads: Uploads = Depends(get_uploads),
    pdf: PdfProcessor = Depends(get_pdf_processor),
):
    """Extraccion automatica (elige natuvo u OCR por pagina.)"""
    # Guarda temporal y procesa
    tmp_path = uploads.save_temp_pdf(file)
    try:
        result = pdf.process(tmp_path)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al extraer texto: {str(e)}")
    finally:
        uploads.cleanup_temp_file(tmp_path)


@router.post("/extract-text/{plantilla_id}")
async def extract_text_with_template(
    plantilla_id: str,
    file: UploadFile = File(...),
    uploads: Uploads = Depends(get_uploads),
    pdf: PdfProcessor = Depends(get_pdf_processor),
    tpl_engine: TemplateEngine = Depends(get_template_engine),
):

    tmp_path = uploads.save_temp_pdf(file)
    try:
        result = pdf.process(tmp_path)

        # Reunir todos los blocks de paginas nativas
        all_blocks: List[Dict] = []
        for p in result.get("pages", []):
            all_blocks.extend(p.get("blocks", []) or [])

        if not all_blocks:
            # No hay palabras detectadas (ni nativo ni OCR)
            result["template_base_extraction"] = {
                "warning": "No se encontraron bloques de texto para aplicar la plantilla.",
                "plantilla": plantilla_id,
            }
            return JSONResponse(content=result)

        try:
            values = tpl_engine.apply(plantilla_id, all_blocks)
            result["template_based_extraction"] = {
                "plantilla": plantilla_id,
                "values": values
            }
        except ValueError as ve:
            raise HTTPException(status_code=404, detail=str(ve))
        except Exception as e:
            result["template_base_extraction"] = {
                "error": f"Error aplicando plantilla: {str(e)}",
                "plantilla": plantilla_id,
            }
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error en extraccion con plantilla: {str(e)} ")
    finally:
        uploads.cleanup_temp_file(tmp_path)
