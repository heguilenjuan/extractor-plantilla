import json, os, threading
from typing import Dict, Optional
from .schemas import Template

class JsonTemplateRepository:
    def __init__(self, path="./data/templates.json"):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f: json.dump({}, f)
        
    def _load(self) -> Dict[str, dict]:
        with self._lock, open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _save(self, data: Dict[str, dict]):
        with self._lock, open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def upsert(self, tpl: Template):
        data = self._load(); data[tpl.id] = tpl.model_dump(); self._save(data)
        
    def get(self, template_id:str) -> Optional[Template]:
        raw = self._load().get(template_id); return Template(**raw) if raw else None
        
    def list_ids(self): return list(self._load().keys())