"""Document text extraction: PDF, DOCX, images (OCR best-effort), plain text."""
from __future__ import annotations

import io
from pathlib import Path


async def extract_text_from_bytes(filename: str, content: bytes, content_type: str = "") -> str:
    name = filename.lower()
    if name.endswith(".txt") or content_type.startswith("text/"):
        return content.decode("utf-8", errors="ignore")

    if name.endswith(".pdf") or "pdf" in content_type:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            pages = [p.extract_text() or "" for p in reader.pages]
            return "\n".join(pages).strip()
        except Exception as exc:
            return f"[PDF extract error: {exc}]"

    if name.endswith(".docx") or "word" in content_type:
        try:
            from docx import Document

            doc = Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs if p.text).strip()
        except Exception as exc:
            return f"[DOCX extract error: {exc}]"

    if name.endswith((".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp")):
        try:
            from PIL import Image
            import pytesseract

            image = Image.open(io.BytesIO(content))
            return pytesseract.image_to_string(image).strip()
        except Exception:
            return "[OCR unavailable — install Tesseract for image text extraction. Please paste the complaint text.]"

    return content.decode("utf-8", errors="ignore")


def save_upload(upload_dir: str, filename: str, content: bytes) -> str:
    path = Path(upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)
    dest = path / safe
    # avoid overwrite
    counter = 1
    stem, suffix = dest.stem, dest.suffix
    while dest.exists():
        dest = path / f"{stem}_{counter}{suffix}"
        counter += 1
    dest.write_bytes(content)
    return str(dest)
