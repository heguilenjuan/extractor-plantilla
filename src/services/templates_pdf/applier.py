import re
from typing import Dict, List, Any
from .schemas import Template, TemplateField


class TemplateApplier:
    def apply(self, tpl: Template, blocks: List[Dict]) -> Dict[str, Any]:
        out = {}
        for name, field in tpl.fields.items():
            out[name] = self._extract(field, blocks)
        return out

    def _extract(self, f: TemplateField, blocks: List[Dict]) -> Any:
        x0, y0, x1, y1 = f.box
        pad = f.pad
        rx0, ry0, rx1, ry1 = x0-pad, y0-pad, x1+pad, y1+pad

        inside = [
            b for b in blocks
            if b.get("page") == f.page
            and (b["coordinates"][2] >= rx0 and b["coordinates"][0] <= rx1
                 and b["coordinates"][3] >= ry0 and b["coordinates"][1] <= ry1)
            and (b.get("text") or "").strip()
        ]
        inside.sort(key=lambda b: (
            round(b["coordinates"][1], 2), round(b["coordinates"][0], 2)))

        text = " ".join(b["text"].strip() for b in inside) if f.join_with_space else "".join(
            b["text"] for b in inside)
        if f.regex and text:
            m = re.search(f.regex, text)
            text = m.group(0) if m else ""

        if f.cast and text:
            text = self._cast(text, f.cast)

        return text

    def _cast(self, v: str, kind: str):
        import re
        if kind == "number":
            v = re.sub(r"[^\d\. \-]", "", v)
            v = v.replace(".", "").replace(",", ".")
            return float(v) if v else None
        return v
