import os
import tempfile
import time
from fastapi import UploadFile, HTTPException

class Uploads:
    """Servicio para manejar archivos temporales subidos."""
    def save_temp_pdf(self, file: UploadFile) -> str:
        """
        Valida que el archivo sea PDF y lo guarda como archivo temporal.
        Devuelve la ruta del archivo temporal.
        """
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                content = file.file.read()  # importante: usar file.file.read() en lugar de await
                tmp.write(content)
                return tmp.name
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error guardando archivo temporal: {str(e)}")

    def cleanup_temp_file(self, path: str) -> None:
        """
        Elimina un archivo temporal con hasta 3 reintentos.
        """
        for attempt in range(3):
            try:
                if os.path.exists(path):
                    os.unlink(path)
                break
            except PermissionError:
                time.sleep(0.1 * (attempt + 1))
            except Exception:
                break
