import fitz
from app.services.extraction.ocr_pipeline import ocr_extract

def extract_text(file_path):

    doc = fitz.open(file_path)
    text = ""

    for page in doc:
        text += page.get_text()

    # agar text empty hai → OCR use karo
    if len(text.strip()) < 50:
        return ocr_extract(file_path)

    return text