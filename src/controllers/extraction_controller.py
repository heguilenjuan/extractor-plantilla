# src/api/controllers/extract_text.py
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
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
    debug: bool = Query(False, description="Devuelve info de anclas y transformaciones"),
    uploads: Uploads = Depends(get_uploads),
    pdf: PdfProcessor = Depends(get_pdf_processor),
    tpl_engine: TemplateEngine = Depends(get_template_engine),
):
    """
    Extrae texto y aplica una plantilla. Devuelve:
      - result.pages (lo que devuelva tu PdfProcessor)
      - template_based_extraction con values y, si debug=True, anclas/transform.
    """
    tmp_path = uploads.save_temp_pdf(file)
    try:
        # 1) Extracción general (nativa/OCR) para obtener blocks por página
        result = pdf.process(tmp_path)

        # 2) Aplanar blocks asegurando metadatos de tamaño y origen top-left
        all_blocks = []
        pages = result.get("pages", []) or []
        for idx, p in enumerate(pages, start=1):
            # tamaños de página si vienen
            pw = p.get("width") or p.get("page_width")
            ph = p.get("height") or p.get("page_height")
            page_num = int(p.get("page", idx))
            origin = (p.get("origin") or "top-left").lower()

            for blk in (p.get("blocks") or []):
                x0, y0, x1, y1 = blk.get("coordinates", [0,0,0,0])

                # Si el extractor trae origen bottom-left, convertir a top-left
                if origin == "bottom-left" and ph:
                    y0, y1 = float(ph) - float(y1), float(ph) - float(y0)

                all_blocks.append({
                    "page": page_num,
                    "coordinates": [float(x0), float(y0), float(x1), float(y1)],
                    "text": blk.get("text", "") or "",
                    "page_width": float(pw) if pw else None,
                    "page_height": float(ph) if ph else None,
                })

        if not all_blocks:
            result["template_based_extraction"] = {
                "warning": "No se encontraron bloques de texto para aplicar la plantilla",
                "plantilla": plantilla_id,
            }
            return JSONResponse(content=result)

        # 3) Aplicar plantilla con anclas (incluye cálculo de T por página)
        try:
            values = tpl_engine.apply_template(plantilla_id, all_blocks, include_debug=debug)
            result["template_based_extraction"] = {
                "plantilla": plantilla_id,
                **values  # {'values':..., 'missing_required':..., 'debug':...}
            }
        except ValueError as ve:
            raise HTTPException(status_code=404, detail=str(ve))
        except Exception as e:
            # Capturamos error pero devolvemos la extracción base
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
