from typing import Dict, Any, List, Tuple
from .types import Coordinates

def rect_intersects(a: Coordinates, b: Coordinates, tol:float = 0.5) -> bool:
    """Verificar si dos rectangulos se intersectan"""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ax0 -= tol; ay0 -= tol; ax1 += tol; ay1 += tol
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)

def cluster_rows_and_order(blocks: List[Dict[str, Any]], row_tol: float = 14.0)-> List[Dict[str, Any]]:
    """Agrupa bloques por filas y ordena de arriba->abajo, izquierda->derecha."""
    if not blocks:
        return []
    
    # Ordenar por coordenada Y
    bs = sorted(blocks, key=lambda b: b["coordinates"][1])
    rows: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = [bs[0]]
    base_y = bs[0]["coordinates"][1]
    
    for b in bs[1:]:
        y0 = b["coordinates"][1]
        if abs(y0 - base_y) <= row_tol:
            current.append(b)
        else:
            current.sort(key=lambda k: k["coordinates"][0])
            rows.append(current)
            current = [b]
            base_y = y0
    
    current.sort(key=lambda k: k["coordinates"][0])
    rows.append(current)
    rows.sort(key=lambda row: row[0]["coordinates"][1])
    
    # Aplanar la lista
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.extend(r)
    return out