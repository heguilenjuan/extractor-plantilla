from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from src.services.templates_pdf.schemas import Template
from src.services.templates_pdf.repo import JsonTemplateRepository
from src.services.templates_pdf.engine import TemplateEngine
from src.services.templates_pdf.builder import TemplateBuilder

router = APIRouter(prefix="/api/v1/templates", tags=["Templates"])
engine = TemplateEngine(JsonTemplateRepository("./data/templates.json"))

@router.get("")
def list_templates(): return {"templates": engine.list_ids()}

@router.post("")
def create_template(payload: Dict[str, Any]):
    try:
        tpl = TemplateBuilder.from_selections(payload["id"], payload["selections"])
        tpl.meta = payload.get("meta", {})
        engine.create_or_update(tpl)
        return {"ok": True, "id":tpl.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/anchors")
def create_template_by_anchors(payload: Dict[str, Any]):
    try:
        tpl = TemplateBuilder.from_anchors(payload["id"], payload["anchors"],payload["blocks"])
        engine.create_or_update(tpl)
        return {"ok": True, "id":tpl.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
