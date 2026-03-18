"""
pdf_parser.py — PyMuPDF (fitz) REMOVED
pdfplumber use karo — pre-built wheel, fast Render install.
"""
import os
from typing import Union

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

from app.services.extraction.ocr_pipeline import ocr_extract, get_text

DOC_TYPE_SIGNALS = {
    "gst_return":      ["GSTIN", "GSTR", "ITC", "outward supplies", "B2B"],
    "bank_statement":  ["Account Number", "IFSC", "Closing Balance", "NEFT", "RTGS"],
    "itr":             ["Income Tax Return", "PAN", "Assessment Year", "TDS"],
    "annual_report":   ["Directors' Report", "Auditor", "Balance Sheet", "Standalone"],
    "legal_notice":    ["NCLT", "DRT", "Court", "Petitioner", "Legal Notice"],
    "sanction_letter": ["Sanction Letter", "Sanctioned Limit", "Rate of Interest"],
    "rating_report":   ["Rating", "CRISIL", "ICRA", "CARE", "Outlook"],
}

def _detect_doc_type(text: str) -> str:
    text_upper = text[:3000].upper()
    scores = {}
    for doc_type, keywords in DOC_TYPE_SIGNALS.items():
        score = sum(1 for kw in keywords if kw.upper() in text_upper)
        if score > 0:
            scores[doc_type] = score
    return max(scores, key=scores.get) if scores else "unknown"

def _extract_excel_text(file_path: str) -> str:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, data_only=True)
        parts = []
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            parts.append(f"[Sheet: {sheet}]")
            for row in ws.iter_rows(values_only=True):
                row_text = "\t".join(str(c) for c in row if c is not None)
                if row_text.strip():
                    parts.append(row_text)
        return "\n".join(parts)
    except Exception as e:
        return f"Excel extraction failed: {e}"

def extract_text(file_path: str) -> Union[str, dict]:
    if not os.path.exists(file_path):
        return {"text": "", "error": f"File not found: {file_path}", "doc_type": "unknown"}

    ext = os.path.splitext(file_path)[1].lower()

    # Excel
    if ext in (".xlsx", ".xls", ".xlsm"):
        text = _extract_excel_text(file_path)
        return {"text": text, "doc_type": _detect_doc_type(text), "ocr_used": False, "file_type": "excel"}

    # CSV
    if ext == ".csv":
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception as e:
            text = f"CSV read failed: {e}"
        return {"text": text, "doc_type": _detect_doc_type(text), "ocr_used": False, "file_type": "csv"}

    # PDF — pdfplumber (replaces PyMuPDF/fitz)
    if PDFPLUMBER_AVAILABLE:
        try:
            full_text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    full_text += page_text + "\n\n"

            # OCR fallback if text too short (scanned PDF)
            if len(full_text.strip()) < 100:
                print(f"📄 Scanned PDF detected — switching to OCR")
                ocr_result = ocr_extract(file_path)
                ocr_text   = get_text(ocr_result)
                return {"text": ocr_text, "doc_type": _detect_doc_type(ocr_text), "ocr_used": True, "file_type": "pdf"}

            return {"text": full_text.strip(), "doc_type": _detect_doc_type(full_text), "ocr_used": False, "file_type": "pdf"}

        except Exception as e:
            print(f"⚠️ pdfplumber failed: {e} — trying OCR")
            ocr_result = ocr_extract(file_path)
            text       = get_text(ocr_result)
            return {"text": text, "doc_type": _detect_doc_type(text), "ocr_used": True, "file_type": "pdf"}

    # Last resort: OCR only
    ocr_result = ocr_extract(file_path)
    text = get_text(ocr_result)
    return {"text": text, "doc_type": _detect_doc_type(text), "ocr_used": True, "file_type": "pdf"}


def get_plain_text(result: Union[str, dict]) -> str:
    if isinstance(result, str):
        return result
    return result.get("text", "")