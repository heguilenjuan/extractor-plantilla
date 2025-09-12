import fitz


def extract_text_from_page(page):
    """ Extrae texto de una página individual (objeto Page)."""
    try:
        return page.get_text("text").strip()
    except Exception as e:
        raise Exception(f"Error extrayendo texto: {str(e)}")


def extract_text_blocks_from_page(page, page_num):
    """Extrae bloques de texto con metadatos de una página individual."""
    all_blocks = []

    try:
        blocks = page.get_text("blocks")

        for block in blocks:
            # Manejar diferentes versiones
            if len(block) == 8:
                x0, y0, x1, y1, text, block_no, block_type, flags = block
            elif len(block) == 7:
                x0, y0, x1, y1, text, block_no, block_type = block
                flags = 0
            else:
                continue

            block_info = {
                "page": page_num,
                "block_number": block_no,
                "coordinates": (x0, y0, x1, y1),
                "text": text.strip(),
                "type": block_type,
                "flags": flags
            }
            
            all_blocks.append(block_info)
    except Exception as e:
        raise Exception(f"Error extrayendo bloques: {str(e)}")

    return all_blocks

# Función original para compatibilidad (recibe ruta de archivo)
def extract_text(pdf_file):
    """Extrae texto de un archivo PDF completo (función legacy)"""
    text = ""
    with fitz.open(pdf_file) as doc:
        for page_num, page in enumerate(doc):
            text += extract_text_from_page(page) + "\n\n"
    return text
