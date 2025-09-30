# src/api/controllers/extract_text.py
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse

from src.services.uploads import Uploads
from src.services.pdfProcessor import PdfProcessor
from src.services.pageExtractor import PageExtractor
from src.services.extractors.native import NativeExtractor
from src.services.extractors.ocr import OCRExtractor

from src.config import create_template_engine
from src.services.templates_pdf.engine import TemplateEngine

router = APIRouter(prefix="/api/v1/extract-text", tags=["Extraction"])

# -------------------- Dependencias --------------------

def get_uploads() -> Uploads:
    return Uploads()

def get_pdf_processor() -> PdfProcessor:
    page_extractor = PageExtractor([NativeExtractor(), OCRExtractor()])
    return PdfProcessor(page_extractor)

def get_template_engine() -> TemplateEngine:
    return create_template_engine()

# -------------------- Endpoints --------------------

@router.post("/")
async def extract_text_from_pdf(
    file: UploadFile = File(...),
    uploads: Uploads = Depends(get_uploads),
    pdf: PdfProcessor = Depends(get_pdf_processor),
):
    """Extracción automática (sin plantilla)"""
    tmp_path = uploads.save_temp_pdf(file)
    try:
        result = pdf.process(tmp_path)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al extraer texto: {str(e)}")
    finally:
        uploads.cleanup_temp_file(tmp_path)

@router.post("/{plantilla_id}")
async def extract_text_with_template(
    plantilla_id: str,
    file: UploadFile = File(...),
    uploads: Uploads = Depends(get_uploads),
    pdf: PdfProcessor = Depends(get_pdf_processor),
    tpl_engine: TemplateEngine = Depends(get_template_engine),
):
    """Extraer texto de PDF aplicando una plantilla específica (usando blocks)"""
    tmp_path = uploads.save_temp_pdf(file)
    try:
        # 1) extracción general (para stats y obtener blocks)
        result = pdf.process(tmp_path)

        # 2) Aplanar blocks de todas las páginas
        all_blocks = []
        for p in result.get("pages", []):
            blocks = p.get("blocks") or []
            all_blocks.extend(blocks)

        if not all_blocks:
            result["template_based_extraction"] = {
                "warning": "No se encontraron bloques de texto para aplicar la plantilla",
                "plantilla": plantilla_id,
            }
            return JSONResponse(content=result)

        # 3) Aplicar plantilla con los blocks
        try:
            values = tpl_engine.apply_template(plantilla_id, all_blocks)
            result["template_based_extraction"] = {
                "plantilla": plantilla_id,
                "values": values
            }
        except ValueError as ve:
            raise HTTPException(status_code=404, detail=str(ve))
        except Exception as e:
            result["template_based_extraction"] = {
                "error": f"Error aplicando plantilla: {str(e)}",
                "plantilla": plantilla_id,
            }

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error en extracción con plantilla: {str(e)}"
        )
    finally:
        uploads.cleanup_temp_file(tmp_path)
