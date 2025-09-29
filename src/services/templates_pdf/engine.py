from .repo import SQLTemplateRepository
from .applier import TemplateApplier
from .schemas import Template


class TemplateEngine:
    def __init__(self, repo: SQLTemplateRepository):
        self.repo = repo
        self.applier = TemplateApplier()

    def create_or_update(self, template_data: dict):
        # convertir del front al template
        template = Template(**template_data)
        self.repo.upsert(template)
        return {"status": "success", "id": template.id}

    def get_template(self, template_id: str):
        return self.repo.get(template_id)

    def list_templates(self):
        return self.repo.list_all()

    def delete_template(self, template_id: str):
        self.repo.delete(template_id)
        return {"status": "deleted", "id": template_id}

    def apply_template(self, template_id: str, pdf_text_blocks: list):
        template = self.repo.get(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' no encontrado")
        return self.applier.apply(template, pdf_text_blocks)