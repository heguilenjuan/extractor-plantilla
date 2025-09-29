import re
from typing import Dict, List, Any
from .schemas import Template


class TemplateApplier:
    def apply(self, template: Template, blocks: List[Dict]) -> Dict[str, Any]:
        out = {}
        for field in template.fields:
            # Encontrasr el box correspondiente al field
            box = next((b for b in template.boxes if b.id == field.boxId), None)
            if not box:
                continue

            out[field.key] = self._extract(field, box, blocks)

        return out

    def _extract(self, field, box, blocks: List[Dict]) -> Any:
        # Logica de extraccion
        x0, y0, x1, y1 = box.x, box.y, box.x + box.w, box.y + box.h
        pad = 2

        # Filtrar bloques dentro del area del box
        inside = [
            b for b in blocks
            if b.get("page") == box.page
            and self._is_inside(b, x0, y0, x1, y1, pad)
            and (b.get("text") or "").strip()
        ]
        # Ordenar y extraer texto
        inside.sort(key=lambda b: (b["coordinates"][1], b["coordinates"][0]))
        text = " ".join(b["text"].strip() for b in inside)

        # Aplicar regex
        if field.regex and text:
            m = re.search(field.regex, text)
            if m:
                text = m.group(
                    1) if m.lastindex and m.lastindex >= 1 else m.group(0)

        # Aplica cast
        if field.cast and text:
            text = self._cast(text, field.cast)

        return text

    def _is_inside(self, block, x0, y0, x1, y1, pad):
        bx0, by0, bx1, by1 = block["coordinates"]
        return (bx1 >= x0 - pad and bx0 <= x1 + pad and by1 >= y0 - pad and by0 <= y1 + pad)

    def _cast(self, v: str, kind: str):
        if kind == "float":
            v = re.sub(r"[^\d,\.]", "", v)
            v = v.replace(",", "").replace(".", "")
            return float(v) if v else None
        return v
