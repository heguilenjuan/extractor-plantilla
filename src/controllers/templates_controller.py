from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from src.services.templates_pdf.schemas import Template
from src.services.templates_pdf.engine import TemplateEngine
from src.config import create_template_engine

router = APIRouter(prefix="/api/v1/templates", tags=["Templates"])

# Crear el engine una sola vez (sin dependencias)
template_engine = create_template_engine()

@router.get("")
def list_templates():
    """Listar todas las plantillas con sus metadatos"""
    try:
        templates = template_engine.list_templates()
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al listar plantillas: {str(e)}")

@router.get("/{template_id}")
def get_template(template_id: str):
    """Obtener una plantilla específica por ID"""
    try:
        template = template_engine.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=404, detail="Plantilla no encontrada")
        return template
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener plantilla: {str(e)}")

@router.post("")
def create_template(payload: Dict[str, Any]):
    """Crear plantilla desde el frontend"""
    try:
        print("📥 Payload recibido:", payload.keys())  # ← Agregar logging
        
        template_data = {
            "id": payload["id"],
            "name": payload.get("name", payload["id"]),
            "meta": payload.get("meta", {}),
            "boxes": payload.get("boxes", []),
            "fields": payload.get("fields", [])
        }

        print("🔧 Template data preparada")  # ← Agregar logging
        print(f"   - ID: {template_data['id']}")
        print(f"   - Name: {template_data['name']}")
        print(f"   - Boxes: {len(template_data['boxes'])}")
        print(f"   - Fields: {len(template_data['fields'])}")

        result = template_engine.create_or_update(template_data)
        print("✅ Template guardado:", result)  # ← Agregar logging
        
        return {"ok": True, "id": result["id"]}

    except Exception as e:
        print("❌ Error en create_template:", str(e))  # ← Agregar logging
        raise HTTPException(status_code=400, detail=str(e))
    
     
@router.delete("/{template_id}")
def delete_template(template_id: str):
    """Eliminar una plantilla"""
    try:
        result = template_engine.delete_template(template_id)
        return {"ok": True, "id": result["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar plantilla: {str(e)}")