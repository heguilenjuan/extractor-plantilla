from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, List

from src.services.uploads import Uploads
from src.services.pdfProcessor import PdfProcessor
from src.services.pageExtractor import PageExtractor
from src.services.extractors.native import NativeExtractor
from src.services.extractors.ocr import OCRExtractor
from src.services.Template.template_manager import TemplateManager

router = APIRouter(prefix="/api/v1", tags=["Extraction"])


def get_uploads() -> Uploads:
    return Uploads()


def get_pdf_processor() -> PdfProcessor:
    page_extractor = PageExtractor([NativeExtractor(), OCRExtractor()])
    return PdfProcessor(page_extractor)


def get_template_manager() -> TemplateManager:
    return TemplateManager()


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
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """Extraccion y luego aplicacion de una plantilla especifica"""
    # Validacion
    if not template_manager.template_exists(plantilla_id):
        raise HTTPException(
            status_code=404, detail=f"Plantilla '{plantilla_id}'")

    tmp_path = uploads.save_temp_pdf(file)
    try:
        result = pdf.process(tmp_path)

        # Reunir todos los blocks de paginas nativas
        all_blocks: List[Dict] = []
        for p in result.get("pages", []):
            if p.get("strategy_used") == "native_text":
                all_blocks.extend(p.get("blocks", []))

        # Aplicar plantilla si hay bloques
        if all_blocks:
            # Si tu manager usa 'proveedor' como el id de plantilla
            tpl_result = template_manager.extract_with_template(
                all_blocks, template_type="factura", proveedor=plantilla_id
            )
            result["template_based_extraction"] = tpl_result
        else:
            result["template_based_extraction"] = {
                "warning": "No hay bloques nativos para aplicar la plantilla.",
                "plantilla": plantilla_id
            }

        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error en extraccion con plantilla: {str(e)} ")
    finally:
        uploads.cleanup_temp_file(tmp_path)
