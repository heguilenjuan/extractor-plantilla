from fastapi import FastAPI
from src.controllers.extraction_controller import router as extraction_router
from src.controllers.templates_controller import router as templates_router

app = FastAPI(title="PDF text Extractor API", version="1.0.0")

# Incluir routers
app.include_router(extraction_router)
app.include_router(templates_router)

@app.get("/")
async def root():
    return {
        "message": "PDF Text Extraction API",
        "endpoints": {
            "GET /api/v1/plantillas": "Lista plantillas disponibles",
            "GET /api/v1/plantillas/{id}": "Detalle de plantilla",
            "GET /api/v1/plantillas/{id}/campos": "Que campos extrae una plantilla especifica",
            "POST /api/v1/extract-text": "Extraccion automatica",
            "POST /api/v1/extract-text/{plantilla_id}": "Extraccion con plantilla"
        
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "PDF Text Extractor"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)