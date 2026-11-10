"""N1 document parsing: text per PDF page, with OCR for scanned pages (no text layer).

Claude reads the PDFs itself (native PDF + vision). This text is what *code* uses: CPT regex (#2a),
quote verification, the injection scan and the RAG query. Without OCR, a faxed scan would fail
every quote check. OCR is local (RapidOCR, ONNX): no patient data leaves the machine.
Tables: pypdf layout mode keeps columns on one line, so a quote from a table row still matches.
"""
import hashlib
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader

MIN_TEXT = 25          # fewer characters than this on a page -> treat it as a scan


@lru_cache(maxsize=1)
def _ocr():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()


def ocr_page(path: Path, index: int) -> str:
    import numpy as np
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(str(path))
    img = pdf[index].render(scale=2.5).to_pil().convert("RGB")
    result, _ = _ocr()(np.array(img))
    return "\n".join(r[1] for r in (result or []))


@lru_cache(maxsize=256)
def _pages(digest: str, path_str: str) -> tuple[tuple[str, bool], ...]:
    path = Path(path_str)
    out = []
    for i, page in enumerate(PdfReader(path_str).pages):
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except Exception:
            text = page.extract_text() or ""
        if len(text.strip()) < MIN_TEXT:
            try:
                out.append((ocr_page(path, i), True))
                continue
            except Exception:
                pass
        out.append((text, False))
    return tuple(out)


def page_texts(path: Path) -> list[str]:
    """Raw text per page ([] if the file is not a readable PDF)."""
    try:
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        return [t for t, _ in _pages(digest, str(path))]
    except Exception:
        return []


def ocr_pages(path: Path) -> list[int]:
    """1-based page numbers that needed OCR (shown to the nurse as 'scanned')."""
    try:
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        return [i + 1 for i, (_, o) in enumerate(_pages(digest, str(path))) if o]
    except Exception:
        return []
