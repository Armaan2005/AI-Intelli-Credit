"""
upload.py  (routes)
-------------------
Upgrades your existing upload_pdf() with:
  ❌ Same filename = silently overwrites existing file
  ❌ No file size limit
  ❌ No file type validation (accepts anything)
  ❌ No document type tagging (GST vs Bank vs Annual Report)
  ❌ Single file only

Fixed:
  ✅ UUID-based unique filenames — no overwrites
  ✅ File size limit (50MB)
  ✅ Allowed types: PDF, Excel, CSV, Images
  ✅ doc_type param — tells extractor what kind of doc it is
  ✅ Multiple files in one request
  ✅ Returns file_id for use in /analyze call
"""
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional

router = APIRouter()

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")

MAX_SIZE_MB = 50
ALLOWED_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".csv",
    ".png", ".jpg", ".jpeg",           # scanned docs
}
ALLOWED_DOC_TYPES = {
    "gst_return", "bank_statement", "itr",
    "annual_report", "legal_notice", "sanction_letter",
    "rating_report", "balance_sheet", "other",
}


@router.post("/")
async def upload_pdf(
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form("other"),       # what kind of document
    app_id:   Optional[str] = Form("default"),     # which credit application
):
    """
    Upload a single document.
    Upgraded from your original — unique filenames, validation, metadata.
    """
    return (await _process_upload(file, doc_type, app_id))[0]


@router.post("/multiple")
async def upload_multiple(
    files:    List[UploadFile] = File(...),
    doc_type: Optional[str]    = Form("other"),
    app_id:   Optional[str]    = Form("default"),
):
    """Upload multiple documents at once."""
    results = []
    for file in files:
        try:
            result = await _process_upload(file, doc_type, app_id)
            results.extend(result)
        except HTTPException as e:
            results.append({"filename": file.filename, "error": e.detail})
    return {"uploaded": len([r for r in results if "error" not in r]), "files": results}


async def _process_upload(
    file: UploadFile,
    doc_type: str,
    app_id: str,
) -> list[dict]:
    """Core upload logic."""

    # ── Validate doc_type ────────────────────────────────────────────────────
    if doc_type not in ALLOWED_DOC_TYPES:
        doc_type = "other"

    # ── Validate file extension ───────────────────────────────────────────────
    original_name = file.filename or "unknown"
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}"
        )

    # ── Read & validate file size ─────────────────────────────────────────────
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f}MB. Max allowed: {MAX_SIZE_MB}MB"
        )

    # ── Save with unique name (UUID) to prevent overwrites ───────────────────
    app_upload_dir = os.path.join(UPLOAD_DIR, app_id)
    os.makedirs(app_upload_dir, exist_ok=True)

    file_id       = str(uuid.uuid4())
    unique_name   = f"{file_id}{ext}"
    file_path     = os.path.join(app_upload_dir, unique_name)

    with open(file_path, "wb") as f:
        f.write(content)

    # ── Trigger background indexing into RAG vector store ────────────────────
    try:
        from app.services.extraction.pdf_parser         import extract_text, get_plain_text
        from app.services.extraction.structured_extractor import extract_structured_data
        from app.services.rag.retriever                 import index_document

        parse_result = extract_text(file_path)
        plain_text   = get_plain_text(parse_result)
        detected_type = parse_result.get("doc_type", doc_type) if isinstance(parse_result, dict) else doc_type

        index_result = index_document(
            text      = plain_text,
            app_id    = app_id,
            doc_type  = detected_type,
            file_name = original_name,
        )
        rag_chunks = index_result.get("chunks_stored", 0)
    except Exception as e:
        print(f"⚠️ RAG indexing failed (non-critical): {e}")
        rag_chunks    = 0
        detected_type = doc_type

    return [{
        "status":        "uploaded",
        "file_id":       file_id,
        "filename":      original_name,
        "saved_as":      unique_name,
        "path":          file_path,
        "doc_type":      detected_type,
        "app_id":        app_id,
        "size_mb":       round(size_mb, 3),
        "rag_chunks":    rag_chunks,
        # Pass this file_path directly to POST /analyze
        "analyze_url":  f"/analyze/?file_path={file_path}&app_id={app_id}",
    }]