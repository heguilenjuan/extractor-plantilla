from typing import Dict, Any, List, Tuple, Optional
from pydantic import BaseModel, Field

class Box(BaseModel):
    id: str
    x: float
    y: float
    w: float
    h: float
    name: Optional[str] = None
    page: int = 1

class TemplateField(BaseModel):
    id: str
    boxId: str
    key: str
    required: bool = True
    normalizers: List[str] = []
    regex: Optional[str] = None
    cast: Optional[str] = None

class Template(BaseModel):
    id: str
    name: str
    boxes: List[Box] = Field(default_factory=list)
    fields: List[TemplateField] = Field(default_factory=list)  # ← CAMBIAR A List
    meta: Dict[str, Any] = {}