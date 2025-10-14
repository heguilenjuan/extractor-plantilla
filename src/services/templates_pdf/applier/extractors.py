import re
from typing import List

def extract_with_regex(raw: str, pattern:str, *, case_sensitive: bool = True) -> str:
    """Extrae texto usando regex. Devuelve el primer grupo no vacio"""
    flags = re.MULTILINE | re.DOTALL
    if not case_sensitive:
        flags |= re.IGNORECASE
    
    try:
        compiled_pattern = re.compile(pattern, flags)
    except re.error:
        return ""
    
    match = compiled_pattern.search(raw)
    if not match:
        return ""
    
    # Buscar el primer grupo no vacio
    groups = match.groups()
    if groups:
        for group in groups:
            if group:
                return group
        return match.group(0)
    return match.group(0)

def extract_value_below_label(text:str, label_pattern: str) -> str:
    """Estrategia para valores en lineas siguientes a etiquetas."""
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        if re.search(label_pattern, line, re.IGNORECASE):
            # Buscar en las siguientes 3 lineas
            for j in range(i + 1, min(i + 4, len(lines))):
                next_line = lines[j].strip()
                amount_match = re.search(r'([0-9][\d,]*\.[\d]{2})', next_line)
                if amount_match:
                    return amount_match.group(1)
    return ""