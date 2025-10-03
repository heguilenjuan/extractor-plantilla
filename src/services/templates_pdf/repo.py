# REPO
import pyodbc
import json
from typing import List, Optional
from .schemas import Box, Template, TemplateField

class SQLTemplateRepository:
    def __init__(self, connection_string: str = None):
        self.conn_string = connection_string

    def get_connection(self):
        return pyodbc.connect(self.conn_string)

    def upsert(self, template: Template):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Serializar boxes y fields como JSON
            boxes_json = json.dumps([box.dict() for box in template.boxes])
            fields_json = json.dumps([field.dict()
                                     for field in template.fields])
            meta_json = json.dumps(template.meta) if template.meta else "{}"

            cursor.execute("""
                            MERGE cmPdfTemplates as target
                            USING (VALUES (?, ?, ?, ?, ?, GETDATE())) AS source (id, name, meta_data, boxes_data, fields_data, updated_at)
                            ON target.id = source.id
                            WHEN MATCHED THEN
                                UPDATE SET name = source.name, meta_data = source.meta_data, boxes_data = source.boxes_data, fields_data = source.fields_data, updated_at = source.updated_at
                            WHEN NOT MATCHED THEN
                                INSERT (id, name, meta_data, boxes_data, fields_data, created_at, updated_at)
                                VALUES (source.id, source.name, source.meta_data, source.boxes_data,
                                source.fields_data, source.updated_at, source.updated_at);
                           """, template.id, template.name, meta_json, boxes_json, fields_json)
            conn.commit()

    def get(self, template_id: str) -> Optional[Template]:
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                           SELECT id, name, meta_data, boxes_data, fields_data
                           FROM cmPdfTemplates
                           WHERE id = ?
            """, template_id)

            row = cursor.fetchone()
            if not row:
                return None

            # Parsear JSON directamente
            boxes = [Box(**box_data)
                     for box_data in json.loads(row.boxes_data)]
            fields = [TemplateField(**field_data)
                      for field_data in json.loads(row.fields_data)]

            return Template(
                id=row.id,
                name=row.name,
                meta=json.loads(row.meta_data) if row.meta_data else {},
                boxes=boxes,
                fields=fields
            )

    def list_ids(self) -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM cmPdfTemplates ORDER BY name")
            return [row[0] for row in cursor.fetchall()]

    def list_all(self) -> List[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, meta_data, created_at, updated_at
                FROM cmPdfTemplates
                ORDER BY name
            """)
            return [
                {
                    "id": row.id,
                    "name": row.name,
                    "meta": json.loads(row.meta_data) if row.meta_data else {},
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in cursor.fetchall()
            ]

    def delete(self, template_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM cmPdfTemplates WHERE id= ?", template_id)
            conn.commit()
