"""Script para instalar Teserract-OCR automaticamente en diferentes sistemas operativos"""
"""Debe ejecutarse con permisos de administrador"""
import sys
import os
import platform
import subprocess
import requests
import shutil


def run_command(command, shell_type=False):
    """Ejecuta un comando de shell y verifica si tuvo exito"""
    try:
        result = subprocess.run(command, shell=shell_type,
                                check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr


def is_tesseract_installed():
    """Verifica si tesseract esta instalado y disponible en el PATH"""
    return shutil.which("tesseract") is not None


def install_windows():
    """Intenta instalar Tesseract en Windows usando el instalador oficial."""
    print("Detectando: Windows")
    tesseract_install_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    # Si ya esta instalado en la ruta común, agregarlo al PATH
    if os.path.isfile(tesseract_install_path):
        print("Tesseract encontraod en ruta predeterminada.")
        return True
    print("Tesseract no encontrado. Intentando descargar e instalar")

    # URL del instalador oficial de Teseract paraWindows (Algo que se debe verificar siempre)
    tesseract_url = "https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe"
    installer_path = os.path.join(os.getenv("TEMP"), "tesseract_installer.exe")

    try:
        print("Descargando instalador")
        response = requests.get(tesseract_url, stream=True)
        response.raise_for_status()

        with open(installer_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(
            f"Ejecutando instalador... Por favor, sigue los pasos en la vena que se abrira.")
        print(f"Importante: asgurate de marca la opcion 'Agregar Tesseract al PATH'")
        subprocess.run([installer_path], check=True)
        print("Instalacion completada. Por favor, cierra y reabre tu terminal")

        return True

    except Exception as e:
        print(f"Error durante la instalacion en Windows: {e}")
        print("Por favor, instala Tesseract manualmente desde:")
        print("https://github.com/UB-Mannheim/tesseract/wiki")

        return False


def install_macos():
    """Instala Tesseract en macOS usando Homebrew."""
    print("🔍 Detectado: macOS")

    # Verificar si Homebrew está instalado
    if not shutil.which("brew"):
        print("❌ Homebrew no encontrado. Instálalo primero desde https://brew.sh")
        return False

    # Comando para instalar Tesseract y los idiomas con Homebrew
    commands = [
        ["brew", "install", "tesseract", "tesseract-lang"]
    ]

    for cmd in commands:
        success, output = run_command(cmd)
        if not success:
            print(f"❌ Error al ejecutar {cmd}: {output}")
            return False
    print("✅ Tesseract instalado correctamente en macOS.")
    return True


def install_linux():
    """Instala Tesseract en distribuciones Linux basadas en Debian/Ubuntu."""
    print("🔍 Detectado: Linux")

    # Comando para instalar Tesseract y el paquete en español
    commands = [
        ["apt-get", "update"],
        ["apt-get", "install", "-y", "tesseract-ocr", "tesseract-ocr-spa"]
    ]

    for cmd in commands:
        success, output = run_command(cmd)
        if not success:
            print(f"❌ Error al ejecutar {cmd}: {output}")
            return False
    print("✅ Tesseract instalado correctamente en Linux.")
    return True


def main():
    """Funcion principal del script de instalacion"""
    print("Verificando e instalando Tesseract-OCR")

    if is_tesseract_installed():
        print("Tesseract ya esta instalado en el sistema.")
        version_output = subprocess.run(
            ["tesseract", "--version"], capture_output=True, text=True)
        print(version_output.stdout)
        return
    # Detecta el sistema operativo
    os_name = platform.system().lower()

    if os_name == "windows":
        success = install_windows()
    elif os_name == "linux":
        success = install_linux()
    elif os_name == "darwin":
        success = install_macos()
    else:
        print(f"Sistema operativo no compatible: {os_name}")
        success = False

    if success and is_tesseract_installed():
        print("Tesseract se ha instalado correctamente")
    else:
        sys.exit(1)


if __name__ == "__main__":
    # Verificar si se está ejecutando con privilegios de administrador
    if os.name != 'nt' and os.geteuid() != 0:  # Unix-like y no es root
        print("⚠️  Este script requiere permisos de administrador (sudo).")
        print("   Ejecuta: sudo python install_tesseract.py")
        sys.exit(1)

    main()
