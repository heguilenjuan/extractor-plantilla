from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field


class TemplateField(BaseModel):
    page: int
    box: Tuple[float, float, float, float]
    pad: int = 2
    join_with_space: bool = True
    regex: Optional[str] = None
    cast: Optional[str] = None


class Template(BaseModel):
    id: str
    fields: Dict[str, TemplateField] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)
