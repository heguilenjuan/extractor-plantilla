from typing import Dict, List
from .schemas import Template, TemplateField


class TemplateBuilder:
    @staticmethod
    def from_selections(template_id: str, selections: List[Dict]) -> Template:
        fields = {
            s["name"]: TemplateField(
                page=int(s["page"]),
                box=tuple(s["box"]),
                pad=int(s.get("pad", 2)),
                regex=s.get("regex"),
                cast=s.get("cast")
            )
            for s in selections
        }
        return Template(id=template_id, fields=fields)

    @staticmethod
    def from_anchors(template_id: str, anchors: List[Dict], blocks: List[Dict]) -> Template:
        fields = {}
        for a in anchors:
            page = a["page"]
            matches = [b for b in blocks if b["page"] ==
                       page and a["anchor_text"].lower() in (b["text"] or "").lower()]
            if not matches:
                continue
            x0, y0, x1, y1 = matches[0]["coordinates"]
            bx = (x1 + a["dx"], y0 + a["dy"], x1 +
                  a["dx"] + a["w"], y0 + a["dy"] + a["h"])
            fields[a["name"]] = TemplateField(
                page=page, box=bx, pad=int(a.get("pad", 2)))
        return Template(id=template_id, fields=fields)
