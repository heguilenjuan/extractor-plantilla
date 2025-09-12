from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from src.services.Template.template_manager import TemplateManager

router = APIRouter(prefix="/api/v1", tags=["Templates"])

template_manager = TemplateManager()

@router.get("/plantillas")
async def get_available_templates():
    """Obtiene el listado de plantillas disponibles"""
    try:
        templates = template_manager.get_all_templates_info()
        return JSONResponse(content={"plantillas": templates})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo plantillas: {str(e)}")

@router.get("/plantillas/{plantilla_id}")
async def get_template_detail(plantilla_id: str):
    """Obtiene información detallada de una plantilla específica"""
    try:
        if not template_manager.template_exists(plantilla_id):
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        
        template_info = template_manager.get_template_info(plantilla_id)
        return JSONResponse(content=template_info)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo plantilla: {str(e)}")

@router.get("/plantillas/{plantilla_id}/campos")
async def get_template_fields(plantilla_id: str):
    """Obtiene los campos que extrae una plantilla específica"""
    try:
        if not template_manager.template_exists(plantilla_id):
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        
        fields = template_manager.get_template_fields(plantilla_id)
        return JSONResponse(content={"campos": fields})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo campos: {str(e)}")