from typing import Dict, Any, List, Tuple, Optional
import numpy as np

Coordinates = Tuple[float, float, float, float]
Point = Tuple[float, float]
TransformMatrix = np.ndarray

class BoxData:
    """Datos de un box de la plantilla"""
    def __init__(self, data: Dict[str, Any]):
        self.id = data["id"]
        self.page = int(data.get("page", 1))
        self.x = float(data["x"])
        self.y = float(data["y"])
        self.w = float(data["w"])
        self.h = float(data["h"])
        self.name = data.get("name")
        
class FieldData:
    """Datos de un campo de la plantilla"""
    def __init__(self, data: Dict[str, Any]):
        self.id = data["id"]
        self.key = data["key"]
        self.box_id = data["boxId"]
        self.required = data.get("required", False)
        self.normalizers = data.get("normalizers", [])
        self.regex = data.get("regex")
        self.cast = data.get("cast")