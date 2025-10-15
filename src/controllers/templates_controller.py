# templates_controller.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from src.config import create_template_engine

router = APIRouter(prefix="/api/v1/templates", tags=["Templates"])
template_engine = create_template_engine()

def _to_int_pages_keyed(pages: Dict[Any, Any]) -> Dict[int, Any]:
    # normaliza claves "1" -> 1
    out: Dict[int, Any] = {}
    for k, v in (pages or {}).items():
        try:
            out[int(k)] = v
        except Exception:
            raise HTTPException(status_code=400, detail=f"meta.pages: clave de página inválida: {k!r}")
    return out

def _validate_anchor(a: Dict[str, Any], page: int, idx: int):
    required = ["id", "x", "y", "pattern"]
    for key in required:
        if key not in a:
            raise HTTPException(status_code=400, detail=f"anchor faltante '{key}' (page {page}, idx {idx})")

    kind = a.get("kind", "regex")
    if kind not in ("text", "regex"):
        raise HTTPException(status_code=400, detail=f"anchor.kind inválido (page {page}, id={a.get('id')}): {kind!r}")

    # searchBox opcional pero, si viene, debe tener dimensiones > 0
    sb = a.get("searchBox")
    if sb:
        for k in ("x", "y", "w", "h"):
            if k not in sb:
                raise HTTPException(status_code=400, detail=f"anchor.searchBox faltante '{k}' (page {page}, id={a.get('id')})")
        if sb["w"] <= 0 or sb["h"] <= 0:
            raise HTTPException(status_code=400, detail=f"anchor.searchBox con tamaño inválido (page {page}, id={a.get('id')})")

def _validate_meta(meta: Dict[str, Any], boxes: List[Dict[str, Any]]):
    # pages es obligatorio para el nuevo flujo
    pages = meta.get("pages")
    if not isinstance(pages, dict) or not pages:
        raise HTTPException(status_code=400, detail="meta.pages es requerido y debe ser un objeto no vacío")

    pages_i = _to_int_pages_keyed(pages)
    meta["pages"] = pages_i  # normalizamos in-place

    # índice de páginas que tienen boxes (para exigir anclas)
    boxes_by_page: Dict[int, int] = {}
    for b in boxes or []:
        p = int(b.get("page", 1))
        boxes_by_page[p] = boxes_by_page.get(p, 0) + 1

    for page, pm in pages_i.items():
        for k in ("pdfWidthBase", "pdfHeightBase", "renderWidth", "renderHeight", "viewportScale"):
            if k not in pm:
                raise HTTPException(status_code=400, detail=f"meta.pages[{page}].{k} faltante")

        # anchors
        anchors = pm.get("anchors", [])
        if not isinstance(anchors, list):
            raise HTTPException(status_code=400, detail=f"meta.pages[{page}].anchors debe ser una lista")

        # Si en esta página hay boxes, pedimos >= 3 anclas
        if boxes_by_page.get(page, 0) > 0 and len(anchors) < 3:
            raise HTTPException(
                status_code=400,
                detail=f"Se requieren al menos 3 anclas en meta.pages[{page}] porque hay boxes en esa página"
            )

        # Validar cada ancla
        for i, a in enumerate(anchors):
            _validate_anchor(a, page, i)

# ---------- endpoints ----------
@router.get("")
def list_templates():
    try:
        templates = template_engine.list_templates()
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar plantillas: {str(e)}")

@router.get("/{template_id}")
def get_template(template_id: str):
    try:
        tpl = template_engine.get_template(template_id)
        if not tpl:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        meta = tpl.meta or {}
        if isinstance(meta.get("pages"), dict):
            meta["pages"] = _to_int_pages_keyed(meta["pages"])
            tpl.meta = meta 
        return tpl
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener plantilla: {str(e)}")

@router.post("")
def create_template(payload: Dict[str, Any]):
    try:
        if "id" not in payload:
            raise HTTPException(status_code=400, detail="Falta 'id' en el payload")

        boxes = payload.get("boxes", [])
        meta  = payload.get("meta", {}) or {}

        try:
            _validate_meta(meta, boxes)
        except HTTPException as e:
            print("❌ validate_meta:", e.detail)  # <---- DEBUG
            raise

        template_data = {
            "id": payload["id"],
            "name": payload.get("name", payload["id"]),
            "meta": meta,
            "boxes": boxes,
            "fields": payload.get("fields", []),
        }
        result = template_engine.create_or_update(template_data)
        return {"ok": True, "id": result["id"]}
    except HTTPException:
        raise
    except Exception as e:
        print("❌ create_template error:", repr(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{template_id}")
def delete_template(template_id: str):
    try:
        result = template_engine.delete_template(template_id)
        return {"ok": True, "id": result["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar plantilla: {str(e)}")


@router.post("/{template_id}/apply")
def apply_template(template_id: str, payload: Dict[str, Any]):
    """
    Aplica la plantilla a un conjunto de bloques de texto (ya extraídos).
    payload: { "blocks": [ { page, coordinates:[x0,y0,x1,y1], text, page_width?, page_height? }, ... ],
               "debug": true|false }
    """
    try:
        blocks = payload.get("blocks") or []
        debug  = bool(payload.get("debug", False))
        if not isinstance(blocks, list) or not blocks:
            raise HTTPException(status_code=400, detail="'blocks' debe ser una lista no vacía")

        result = template_engine.apply_template(template_id, blocks)
        # si tu applier soporta include_debug, pásalo desde acá (ajusta engine y applier si querés)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al aplicar plantilla: {str(e)}")
