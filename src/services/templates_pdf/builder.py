#Builder
from uuid import uuid4
from typing import Dict, List
from .schemas import Box, Template, TemplateField


class TemplateBuilder:
    def __init__(self, name: str):
        self.template = Template(
            id=str(uuid4()),
            name=name,
            boxes=[],
            fields=[],
            meta={}
        )

    def add_box(self, x: float, y: float, w: float, h: float, name: str = None, page: int = 1):
        box = Box(
            id=str(uuid4()),
            x=x,
            y=y,
            w=w,
            h=h,
            page=page,
            name=name
        )
        self.template.boxes.append(box)
        return box.id

    def add_field(self, box_id: str, key: str, regex: str = None, cast: str = None, required: bool = True):
        field = TemplateField(
            id=str(uuid4()),
            boxId=box_id,
            key=key,
            regex=regex,
            cast=cast,
            required=required
        )
        self.template.fields.append(field)
        return self

    def set_meta(self, meta: dict):
        self.template.meta.update(meta)
        return self

    def build(self):
        return self.template
