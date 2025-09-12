from typing import Dict, Any, List
import re


class CoordinateBasedTemplate:
    """Plantilla que extrae datos basados en coordenadas especificas"""

    def __init__(self, template_name: str, field_definitions: Dict):
        self.template_name = template_name
        self.field_definitions = field_definitions

    def extract_from_blocks(self, blocks: List[Dict]) -> Dict[str, Any]:
        """Extrae datos basados en las coordenadas  de los bloques"""
        resultados = {}

        for block in blocks:
            x0, y0, x1, y1 = block['coordinates']
            text = block['text'].strip()
            page = block['page']

            # Verificar cada campo definido en la plantilla
            for field_name, field_config in self.field_definitions.items():
                # Verificar si este bloque esta en la zona del campo
                if self._is_in_zone(x0, y0, x1, y1, field_config, page):
                    # Procesar el valor segun el tipo de campo
                    processed_value = self._process_field(text, field_config)
                    if processed_value:
                        resultados[field_name] = processed_value

        return resultados

    def _is_in_zone(self, x0: float, y0: float, x1: float, y1: float, field_config: Dict, page: int) -> bool:
        """Verifica si el bloque esta dentro de la zona definida para el campo"""
        if 'page' in field_config and field_config['page'] != page:
            return False

        # Verificar coordenadas
        tolerance = field_config.get('tolerance', 5)

        if 'x_range' in field_config:
            x_min, x_max = field_config['x_range']
            if not (x_min - tolerance <= x0 <= x_max + tolerance):
                return False

        if 'y_range' in field_config:
            y_min, y_max = field_config['y_range']
            if not (y_min - tolerance <= y0 <= y_max + tolerance):
                return False

        return True

    def _process_field(self, text: str, field_config: Dict) -> Any:
        """Procesa el texto extraido segun el tipo de campo"""
        field_type = field_config.get('type', 'text')

        if field_type == 'number':
            # Extraer numeros
            numbers = re.findall(r'[\d,]+\.?\d*', text)
            return numbers[0] if numbers else None
        
        elif field_type == 'currency':
            # Extraer montos monetarios
            amounts = re.findall(r'[\$]?[\d,]+\.?\d*', text)
            return amounts[0] if amounts else None
        
        elif field_type == 'date':
            # Extraer fechas
            dates = re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
            return dates[0] if dates else None
        
        elif field_type == 'regex':
            # Usar regex personalizada
            pattern = field_config.get('pattern', '')
            match = re.search(pattern, text)
            return match.group(1) if match else None
            
        else:  # text
            return text if text else None