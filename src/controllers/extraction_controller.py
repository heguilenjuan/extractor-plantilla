from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
import logging

from src.services.uploads import Uploads
from src.services.pdfProcessor import PdfProcessor
from src.services.pageExtractor import PageExtractor
from src.services.extractors.combined import CombinedExtractor

from src.services.fields.totals import extract_totals, infer_proveedor_from_template_id

from src.config import create_template_engine
from src.services.templates_pdf.engine import TemplateEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/extract-text", tags=["Extraction"])


# -------------------- Dependencias --------------------
def get_uploads() -> Uploads:
    return Uploads()

def get_pdf_processor() -> PdfProcessor:
    strategies = [CombinedExtractor(ocr_always=True, dpi=300, lang="spa+eng", min_conf=40)]
    page_extractor = PageExtractor(strategies)
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
    """Extracción automática"""
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
        # 1) Extracción general
        result = pdf.process(tmp_path)

        # 2) Aplanar blocks, metadatos de tamaño y origen top-left
        all_blocks = []
        pages = result.get("pages", []) or []

        for idx, p in enumerate(pages, start=1):
            pw = p.get("width") or p.get("page_width")
            ph = p.get("height") or p.get("page_height")
            page_num = int(p.get("page", idx))
            origin = (p.get("origin") or "top-left").lower()

            for blk in (p.get("blocks") or []):
                x0, y0, x1, y1 = blk.get("coordinates", [0, 0, 0, 0])

                # Si el extractor trae origen bottom-left, convertir a top-left
                if origin == "bottom-left" and ph:
                    y0, y1 = float(ph) - float(y1), float(ph) - float(y0)

                all_blocks.append({
                    "page": page_num,
                    "coordinates": [float(x0), float(y0), float(x1), float(y1)],
                    "text": blk.get("text", "") or "",
                    "page_width": float(pw) if pw else None,
                    "page_height": float(ph) if ph else None,
                    "source": blk.get("source"),
                    "kind": blk.get("kind"),
                    "conf": blk.get("conf"),
                })

        if not all_blocks:
            result["template_based_extraction"] = {
                "warning": "No se encontraron bloques de texto para aplicar la plantilla",
                "plantilla": plantilla_id,
            }
            return JSONResponse(content=result)

        # 3) Aplicar plantilla con anclas
        try:
            values = tpl_engine.apply_template(plantilla_id, all_blocks, include_debug=debug)
            result["template_based_extraction"] = {
                "plantilla": plantilla_id,
                **values
            }
        except ValueError as ve:
            raise HTTPException(status_code=404, detail=str(ve))
        except Exception as e:
            logger.exception("Error aplicando plantilla")
            result["template_based_extraction"] = {
                "error": f"Error aplicando plantilla: {str(e)}",
                "plantilla": plantilla_id,
            }

        # 4) Totales por proveedor (Guerrini, Pirelli, etc.)
        try:
            proveedor = infer_proveedor_from_template_id(plantilla_id)
            totals = extract_totals(all_blocks, proveedor=proveedor, y_tolerance=24, x_min_gap=6.0)
            tbx = result.get("template_based_extraction", {})
            vals = tbx.setdefault("values", {})

            if totals.get("SUBTOTAL"):
                    vals["subtotal"] = totals["SUBTOTAL"]
            if totals.get("IVA_21"):
                    vals["iva_21"] = totals["IVA_21"]
            if totals.get("PERCEP"):
                    # si tenés campos separados de IIBB/perc, adaptá aquí
                    vals["percep_iibb"] = totals["PERCEP"]
            if totals.get("TOTAL") and (not vals.get("total") or vals.get("total") == vals.get("subtotal")):
                    vals["total"] = totals["TOTAL"]

            result["template_based_extraction"]["values"] = vals
        except Exception:
            pass

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en extracción con plantilla: {str(e)}")
    finally:
        uploads.cleanup_temp_file(tmp_path)
