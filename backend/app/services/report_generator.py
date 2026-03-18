# services/report_generator.py
# Simple wrapper — actual logic routes/report.py mein hai
from app.routes.report import build_cam_pdf

def generate_report(data: dict, filename: str = "report.pdf") -> str:
    """
    Backward-compatible wrapper.
    analyze.py import karta tha: from app.services.report_generator import generate_report
    Ab yeh routes/report.py ki professional build_cam_pdf() call karta hai.
    """
    return build_cam_pdf(data, filename, data.get("meta", {}).get("company", "Company"))