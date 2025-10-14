from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.controllers.extraction_controller import router as extraction_router
from src.controllers.templates_controller import router as templates_router
from src.config import create_template_engine

app = FastAPI(title="PDF Text Extractor API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crea el template engine
template_engine = create_template_engine()

# Incluir routers
app.include_router(extraction_router)
app.include_router(templates_router) 

def get_template_engine():
    return template_engine

@app.get("/")
async def root():
    return {
        "message": "PDF Text Extraction API",
        "endpoints": {
            # Plantillas
            "GET /api/v1/templates": "Lista plantillas disponibles",
            "GET /api/v1/templates/{id}": "Obtener plantilla específica",
            "POST /api/v1/templates": "Crear/actualizar plantilla",
            "DELETE /api/v1/templates/{id}": "Eliminar plantilla",
            # Extracción
            "POST /api/v1/extract-text/{plantilla_id}": "Extracción con plantilla",
        },
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "PDF Text Extractor"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
