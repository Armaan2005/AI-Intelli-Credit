import pytesseract
from pdf2image import convert_from_path
import os

def ocr_extract(file_path):

    images = convert_from_path(file_path)
    full_text = ""

    for i, img in enumerate(images):
        text = pytesseract.image_to_string(img)
        full_text += text + "\n"

    return full_text