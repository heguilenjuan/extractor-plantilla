from .coordinate_based_template import CoordinateBasedTemplate
from typing import Dict


class FacturaTemplate(CoordinateBasedTemplate):
    """Plantilla especifica para facturas de un proveedor especifico"""

    def __init__(self, proveedor: str = "default"):
        # Definir las zonas donde se encuentran los datos en la factura
        field_definitions = self._get_field_definitions(proveedor)
        super().__init__(f"factura_{proveedor}", field_definitions)

    def _get_field_definitions(self, proveedor: str) -> Dict:
        """Obtener definiciones de ampos según el proveedor"""

        # Ejemplo para un proveedor espcífico
        if proveedor == "proveedor_a":
            return {
                "numero_factura": {
                    "x_range": (400, 500),
                    "y_range": (50, 70),
                    "page": 0,
                    "type": "text",
                    "tolerance": 10
                },
                "fecha_emision": {
                    "x_range": (400, 500),
                    "y_range": (80, 100),
                    "page": 0,
                    "type": "text"
                },
                "ruc_cliente": {
                    "x_range": (50, 200),
                    "y_range": (150, 170),
                    "page": 0,
                    "type": "number"
                },
                "subtotal": {
                    "x_range": (400, 500),
                    "y_range": (300, 320),
                    "page": 0,
                    "type": "currency"
                },
                "iva": {
                    "x_range": (400, 500),
                    "y_range": (330, 350),
                    "page": 0,
                    "type": "currency"
                },
                "total": {
                    "x_range": (400, 500),
                    "y_range": (360, 380),
                    "page": 0,
                    "type": "currency"
                }
            }
        # Plantilla por defecto
        else:
            return {

            }

    def detect_proveedor(self, text: str) -> str:
        """Detectar automaticamente el proveedor basado en text"""
        if "PROVEEDOR_A" in text.upper():
            return "proveedor_a"
        elif "EMPRESA_B" in text.upper():
            return "empresa_b"
        return "default"
