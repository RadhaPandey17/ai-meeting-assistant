"""
Document text extraction (PDF / DOCX / DOC / TXT / MD) for the Document RAG input source.

The returned text keeps "[Page N]" markers for PDFs, so the hybrid RAG chunks carry page
information and the LLM can cite pages in its answers.
Scanned PDF pages are OCR'd automatically when Tesseract (+ pytesseract, pdf2image) is installed.
"""
import os
import shutil
import subprocess
import tempfile
from typing import List

DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}


class DocumentExtractionError(Exception):
    pass


def is_document(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in DOCUMENT_EXTENSIONS


def extract_document_text(path: str) -> str:
    """Return the full text of a document, or raise DocumentExtractionError."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text = _read_pdf(path)
    elif ext == ".docx":
        text = _read_docx(path)
    elif ext == ".doc":
        text = _read_doc(path)
    elif ext in (".txt", ".md"):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    else:
        raise DocumentExtractionError(f"Unsupported document type: {ext}")

    if not text.strip():
        raise DocumentExtractionError(
            "No readable text found in the document. If it is a scanned file, install Tesseract OCR "
            "(+ pytesseract and pdf2image) so it can be scanned."
        )
    return text.strip()


# ── PDF ──────────────────────────────────────────────────────────────────────
def _read_pdf(path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise DocumentExtractionError("PDF is password protected.")

    parts: List[str] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if len(text) < 20:  # likely a scanned page -> OCR
            text = _ocr_pdf_page(path, i) or text
        if text:
            parts.append(f"[Page {i}]\n{text}")
    return "\n\n".join(parts)


def _ocr_pdf_page(path: str, page_number: int):
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        return None
    if not shutil.which("tesseract"):
        return None
    try:
        images = convert_from_path(path, dpi=200, first_page=page_number, last_page=page_number)
        return "\n".join(pytesseract.image_to_string(img) for img in images).strip() or None
    except Exception as e:
        print(f"[DocExtractor] OCR failed on page {page_number}: {e}")
        return None


# ── DOCX / DOC ───────────────────────────────────────────────────────────────
def _read_docx(path: str) -> str:
    from docx import Document

    doc = Document(path)
    lines: List[str] = []
    for block in doc.iter_inner_content():  # paragraphs + tables in document order
        if hasattr(block, "rows"):
            for row in block.rows:
                cells = []
                for c in row.cells:
                    t = c.text.strip()
                    if t and (not cells or cells[-1] != t):  # skip merged-cell duplicates
                        cells.append(t)
                if cells:
                    lines.append(" | ".join(cells))
        elif block.text.strip():
            lines.append(block.text.strip())
    return "\n\n".join(lines)


def _read_doc(path: str) -> str:
    """Legacy .doc -> convert to .docx using LibreOffice, then read."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise DocumentExtractionError(
            "Legacy .doc files need LibreOffice installed. Alternatively save the file as .docx and upload again."
        )
    with tempfile.TemporaryDirectory() as tmp:
        try:
            subprocess.run([soffice, "--headless", "--convert-to", "docx", "--outdir", tmp, path],
                           check=True, capture_output=True, timeout=120)
        except (subprocess.SubprocessError, OSError) as e:
            raise DocumentExtractionError(f"Could not convert .doc file: {e}")
        converted = os.path.join(tmp, os.path.splitext(os.path.basename(path))[0] + ".docx")
        if not os.path.exists(converted):
            raise DocumentExtractionError("Could not convert .doc file.")
        return _read_docx(converted)
