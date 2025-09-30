# config.py
import os
from dotenv import load_dotenv
import pyodbc
from src.services.templates_pdf.engine import TemplateEngine
from src.services.templates_pdf.repo import SQLTemplateRepository
load_dotenv()


def create_template_engine():
    repo = SQLTemplateRepository()
    return TemplateEngine(repo=repo)


def get_db_connection_string():
    # Para SQL Server con instancia nombrada
    server = os.getenv('DB_SERVER', 'SERVER2012\\PARADIGMA')
    database = os.getenv('DB_NAME', 'PDF_Templates')
    username = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')

    possible_drivers = [
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 13 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server"
    ]

    available_drivers = [d for d in pyodbc.drivers() if any(
        pd in d for pd in possible_drivers)]

    if not available_drivers:
        raise Exception("""
        ❌ No se encontraron drivers ODBC para SQL Server.
        
        SOLUCIÓN:
        1. Descarga e instala 'ODBC Driver 17 for SQL Server' desde:
           https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
        
        2. O instala SQL Server Management Studio (SSMS) que incluye los drivers
        """)

    driver = available_drivers[0]
    print(f"✅ Usando driver: {driver}")
    # Opción 1: Si usas autenticación de Windows
    if not username and not password:
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )

    # Opción 2: Con usuario/contraseña
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "TrustServerCertificate=yes;"
    )


def create_template_engine():
    from src.services.templates_pdf.repo import SQLTemplateRepository
    repo = SQLTemplateRepository(get_db_connection_string())
    from src.services.templates_pdf.engine import TemplateEngine
    return TemplateEngine(repo)
