import re
from typing import Dict, Any, List
from .factura_template import FacturaTemplate


class TemplateManager:
    """Gestiona plantillas basadas en coordenadas"""

    def __init__(self):
        self.templates = {}

    def get_all_templates_info(self):
        """
        Devuelve un resumen de todas las plantillas registradas
        """
        info = {}
        for name, template in self.templates.items():
            if isinstance(template, dict):
                info[name] = {
                    "num_campos": len(template),
                    "campos": list(template.keys())
                }
            else:
                info[name] = str(template)
        return info

    def template_exists(self, plantilla_id: str) -> bool:
        """Verifica si el template con el ID/nombre dado existe"""
        return plantilla_id in self.templates

    def create_template_from_analysis(self, blocks: List[Dict], sample_data: Dict = None):
        """Crear plantilla automaticamente analizando un documento de muestra"""

        # Esta funcion puede ayudar a generar plantillas automaticas

        template_def = {}

        if sample_data:
            for field_name, field_value in sample_data.items():
                # Buscar el campo en los bloques
                for block in blocks:
                    if field_value in block['text']:
                        x0, y0, x1, y1 = block['coordinates']
                        template_def[field_name] = {
                            "x_range": (x0 - 5, x1 + 5),
                            "y_range": (y0 - 5, y1 + 5),
                            "page": block['page'],
                            "type": self._guess_field_type(field_value)
                        }
                        break
        return template_def

    def _guess_field_type(self, value: str) -> str:
        """Intentar adivinar el tipo de campo basado en el valor"""
        if re.match(r'^\d{1,2}[/-]d{1,2}[/-]\d{2,4}$', value):
            return 'date'
        elif re.match(r'^[\$]?[\d,]+\d*$', value):
            return 'currency'
        elif re.match(r'^\d+$', value):
            return 'number'
        return 'text'

    def extract_with_template(self, blocks: List[Dict], template_type: str = "factura", proveedor: str = None) -> Dict[str, Any]:
        """Extraer datos usando plantilla especifica"""
        if template_type == "factura":
            template = FacturaTemplate(proveedor)
            return template.extract_from_blocks(blocks)
        return {}
