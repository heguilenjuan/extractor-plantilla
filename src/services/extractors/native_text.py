# src/services/extractors/native_text.py
import fitz

def extract_text_from_page(page):
    try:
        return page.get_text("text").strip()
    except Exception as e:
        raise Exception(f"Error extrayendo texto: {str(e)}")

def extract_text_blocks_from_page(page, page_num):
    """Bloques nativos de PyMuPDF. Solo texto (type==0)."""
    all_blocks = []
    try:
        blocks = page.get_text("blocks")  # [(x0,y0,x1,y1,text, block_no, block_type, flags)]
        for block in blocks:
            if len(block) < 7:
                continue
            x0, y0, x1, y1 = float(block[0]), float(block[1]), float(block[2]), float(block[3])
            text = (block[4] or "").strip()
            block_no = int(block[5])
            block_type = int(block[6])  # 0=text
            flags = int(block[7]) if len(block) >= 8 else 0
            if block_type != 0 or not text:
                continue
            all_blocks.append({
                "page": page_num,
                "block_number": block_no,
                "coordinates": [x0, y0, x1, y1],
                "text": text,
                "type": 0,
                "flags": flags,
            })
    except Exception as e:
        raise Exception(f"Error extrayendo bloques: {str(e)}")
    return all_blocks

def extract_text(pdf_file):
    text = ""
    with fitz.open(pdf_file) as doc:
        for _, page in enumerate(doc, start=1):
            text += extract_text_from_page(page) + "\n\n"
    return text
