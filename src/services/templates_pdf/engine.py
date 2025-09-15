from .repo import JsonTemplateRepository
from .applier import TemplateApplier


class TemplateEngine:
    def __init__(self, repo: JsonTemplateRepository):
        self.repo = repo
        self.applier = TemplateApplier()

    def create_or_update(self, tpl): self.repo.upsert(tpl)
    def list_ids(self): return self.repo.list_ids()

    def apply(self, template_id: str, blocks):
        tpl = self.repo.get(template_id)
        if not tpl:
            raise ValueError(f"Plantilla '{template_id}' no encontrada")
        return self.applier.apply(tpl, blocks)
