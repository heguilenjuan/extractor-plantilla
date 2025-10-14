from typing import Dict, Any, List, Tuple
import numpy as np

from .normalizers import apply_normalizers
from .geometry import cluster_rows_and_order, rect_intersects
from .transforms import to_pdf_scale_from_meta, transform_box, fit_affine, fit_similarity
from .anchors import find_anchor_Q
from .extractors import extract_with_regex, extract_value_below_label
from .types import BoxData, FieldData

class TemplateApplier:
    """Aplica plantillas sobre bloques de texto extraídos de PDF."""
    
    def apply(self, template, pdf_text_blocks: List[Dict[str, Any]], *, 
              include_debug: bool = False) -> Dict[str, Any]:
        # Inicialización
        meta = template.meta or {}
        pages_meta = self._prepare_pages_meta(meta)
        boxes = self._prepare_boxes(template.boxes)
        fields = self._prepare_fields(template.fields)
        
        # Agrupar bloques por página
        by_page, page_size = self._group_blocks_by_page(pdf_text_blocks)
        
        # Procesar páginas
        box_text_cache, debug_data = self._process_pages(
            boxes, by_page, page_size, pages_meta, meta, include_debug
        )
        
        # Extraer campos
        result = self._extract_fields(fields, box_text_cache, include_debug)
        
        # Agregar debug si es necesario
        if include_debug:
            result["debug"] = debug_data
            
        return result

    def _prepare_pages_meta(self, meta: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """Prepara metadatos de páginas."""
        pages_meta = {}
        if "pages" in meta:
            for k, v in meta["pages"].items():
                pages_meta[int(k)] = v
        return pages_meta

    def _prepare_boxes(self, boxes: List[Any]) -> List[Dict[str, Any]]:
        """Convierte boxes a diccionarios."""
        return [b if isinstance(b, dict) else b.model_dump() for b in (boxes or [])]

    def _prepare_fields(self, fields: List[Any]) -> List[Dict[str, Any]]:
        """Convierte fields a diccionarios."""
        return [f if isinstance(f, dict) else f.model_dump() for f in (fields or [])]

    def _group_blocks_by_page(self, pdf_text_blocks: List[Dict[str, Any]]) -> Tuple:
        """Agrupa bloques por página y calcula tamaños."""
        by_page = {}
        page_size = {}
        
        for block in pdf_text_blocks:
            page_num = int(block.get("page", 1))
            by_page.setdefault(page_num, []).append(block)
            
            pw = block.get("page_width")
            ph = block.get("page_height")
            if pw and ph:
                page_size[page_num] = (float(pw), float(ph))
        
        # Fallback para páginas sin tamaño
        for page_num, blocks in by_page.items():
            if page_num not in page_size:
                max_x = max((b["coordinates"][2] for b in blocks), default=600.0)
                max_y = max((b["coordinates"][3] for b in blocks), default=800.0)
                page_size[page_num] = (max_x, max_y)
        
        return by_page, page_size

    def _process_pages(self, boxes, by_page, page_size, pages_meta, meta, include_debug):
        """Procesa todas las páginas y extrae texto de boxes."""
        T_by_page = {}
        anchors_debug = {}
        box_text_cache = {}
        boxes_debug = {}

        # Calcular transformaciones por página
        for page_num, blocks in by_page.items():
            T_by_page[page_num] = self._calculate_page_transform(
                page_num, blocks, pages_meta, page_size, meta, anchors_debug, include_debug
            )

        # Extraer texto de cada box
        for box in boxes:
            page_num = int(box.get("page", 1))
            T = T_by_page.get(page_num, self._get_fallback_transform(page_num, page_size, meta))
            
            # Transformar box y extraer texto
            pdf_rect = transform_box(T, box)
            text = self._extract_text_from_rect(pdf_rect, by_page.get(page_num, []))
            box_text_cache[box["id"]] = text
            
            if include_debug:
                boxes_debug[box["id"]] = {
                    "box_name": box.get("name"),
                    "page": page_num,
                    "rect_pdf": pdf_rect,
                    "text_preview": text[:300]
                }

        debug_data = {
            "anchors": anchors_debug,
            "transforms": {p: T.tolist() for p, T in T_by_page.items()},
            "boxes": boxes_debug,
        }

        return box_text_cache, debug_data

    def _calculate_page_transform(self, page_num, blocks, pages_meta, page_size, meta, anchors_debug, include_debug):
        """Calcula transformación para una página."""
        pm = pages_meta.get(page_num, {})
        if not pm:
            return self._get_fallback_transform(page_num, page_size, meta)

        scale = to_pdf_scale_from_meta(pm)
        src_points = []
        dst_points = []
        found_anchors = []

        # Buscar anclas
        for anchor in (pm.get("anchors") or []):
            result = find_anchor_Q(anchor, blocks, pm)
            if result is None:
                found_anchors.append({"id": anchor.get("id"), "matched": False})
                continue
                
            u, v, block = result
            src_points.append((float(anchor["x"]), float(anchor["y"])))
            dst_points.append((u, v))
            found_anchors.append({
                "id": anchor.get("id"),
                "matched": True,
                "expected": (float(anchor["x"]) * scale, float(anchor["y"]) * scale),
                "found": (u, v)
            })

        # Calcular transformación basada en anclas encontradas
        if len(src_points) >= 3:
            T = fit_affine(src_points, dst_points)
        elif len(src_points) == 2:
            T = fit_similarity(src_points[0], src_points[1], dst_points[0], dst_points[1])
        elif len(src_points) == 1:
            exp_u = src_points[0][0] * scale
            exp_v = src_points[0][1] * scale
            du = dst_points[0][0] - exp_u
            dv = dst_points[0][1] - exp_v
            T = np.array([[scale, 0, du], [0, scale, dv]], dtype=float)
        else:
            T = np.array([[scale, 0, 0], [0, scale, 0]], dtype=float)

        if include_debug:
            anchors_debug[page_num] = {"found": found_anchors, "T": T.tolist()}

        return T

    def _get_fallback_transform(self, page_num, page_size, meta):
        """Transformación fallback cuando no hay metadatos de página."""
        pw, ph = page_size.get(page_num, (600.0, 800.0))
        rw = float(meta.get("renderWidth") or 600.0)
        rh = float(meta.get("renderHeight") or 800.0)
        sx, sy = pw / rw, ph / rh
        return np.array([[sx, 0, 0], [0, sy, 0]], dtype=float)

    def _extract_text_from_rect(self, rect, page_blocks):
        """Extrae texto de un rectángulo en los bloques de página."""
        inside = [block for block in page_blocks 
                 if rect_intersects(rect, tuple(block["coordinates"]), tol=0.75)]
        
        if not inside:
            return ""
            
        ordered_blocks = cluster_rows_and_order(inside)
        text = "\n".join(block.get("text", "") for block in ordered_blocks).strip()
        return text

    def _extract_fields(self, fields, box_text_cache, include_debug):
        """Extrae valores de campos usando las estrategias definidas."""
        out = {}
        missing_required = []
        field_debug = {} if include_debug else None

        for field in fields:
            key = field["key"]
            box_id = field["boxId"]
            raw_text = box_text_cache.get(box_id, "")
            
            # Extraer valor
            value = self._extract_field_value(field, raw_text)
            
            # Aplicar normalizadores y cast
            value = apply_normalizers(value, field.get("normalizers"))
            value = self._apply_cast(value, field.get("cast"))
            
            # Verificar requeridos
            if field.get("required") and not value:
                missing_required.append(key)
                
            out[key] = value
            
            if include_debug:
                field_debug[key] = {
                    "raw_text_preview": raw_text[:200],
                    "pattern": field.get("regex"),
                    "matched_value": value
                }

        result = {"values": out, "missing_required": missing_required}
        
        if include_debug and field_debug:
            result["field_debug"] = field_debug
            
        return result

    def _extract_field_value(self, field, raw_text):
        """Extrae valor de un campo usando regex y estrategias alternativas."""
        pattern = field.get("regex")
        if not pattern:
            return raw_text

        # Estrategia principal: regex
        value = extract_with_regex(raw_text, pattern, case_sensitive=True)
        
        # Estrategia alternativa para campos de monto
        if not value and field["key"] in ["subtotal", "iva_21", "percep_iibb", "total"]:
            label_pattern = pattern.split('(')[0].rstrip('\\s*')
            value = extract_value_below_label(raw_text, label_pattern)
            
        return value

    def _apply_cast(self, value, cast_type):
        """Aplica conversión de tipo al valor."""
        if not value or not cast_type:
            return value
            
        try:
            if cast_type == "int":
                return int(value.replace(",", "").replace(".", ""))
            elif cast_type in ("float", "decimal"):
                return float(value.replace(",", ""))
        except (ValueError, TypeError):
            pass
            
        return value