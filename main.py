# src/main.py
from fastapi import FastAPI
from src.controllers.extraction_controller import router as extraction_router
from src.controllers.templates_controller import router as templates_router

app = FastAPI(title="PDF Text Extractor API", version="1.0.0")

# Incluir routers
app.include_router(extraction_router)   # /api/v1/extract-text...
app.include_router(templates_router)    # /api/v1/templates...

@app.get("/")
async def root():
    return {
        "message": "PDF Text Extraction API",
        "endpoints": {
            # Plantillas
            "GET /api/v1/templates": "Lista plantillas disponibles",
            "POST /api/v1/templates": "Crear/actualizar plantilla (por selección)",
            "POST /api/v1/templates/anchors": "Crear plantilla (por anclas)",
            "POST /api/v1/templates/{id}/apply": "Aplicar plantilla a un PDF",
            # Extracción
            "POST /api/v1/extract-text": "Extracción automática (nativo + OCR)",
            "POST /api/v1/extract-text/{plantilla_id}": "Extracción con plantilla",
        },
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "PDF Text Extractor"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
