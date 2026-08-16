"""
Tests for extract_pdf_text.py's OCR-fallback control flow — specifically
finding #18, that one page's OCR failure no longer disables OCR for every
later page in the same file.

pdfplumber/PyMuPDF/pytesseract aren't installed in every environment this
runs in (they're heavy, native-code dependencies) — extract_pdf_text.py
imports them at module level, so real installs would otherwise be
required just to import the module under test. Minimal fake modules are
installed into sys.modules before import so the control flow (which is
what finding #18 is actually about) can be tested without them; Pillow
is a real, lightweight dependency here since ocr_page() needs a real
Image object to hand back from a "page render".
"""
import io
import sys
import types

import pytest
from PIL import Image


def _tiny_png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buf, "PNG")
    return buf.getvalue()


def _install_fake_pdf_stack(monkeypatch, page_texts, ocr_failures=frozenset()):
    """
    page_texts: list of str|None, one per page — None means pdfplumber
    found no extractable text, triggering the OCR fallback for that page.
    ocr_failures: set of 1-indexed *OCR call* numbers (in page order, since
    only pages needing OCR call pytesseract) that should raise instead of
    returning text.
    """

    class FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class FakePdf:
        metadata = {}
        pages = [FakePage(t) for t in page_texts]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_pdfplumber = types.ModuleType("pdfplumber")
    fake_pdfplumber.open = lambda path: FakePdf()

    class FakePixmap:
        def tobytes(self, fmt):
            return _tiny_png_bytes()

    class FakeMuPage:
        def get_pixmap(self, matrix=None):
            return FakePixmap()

    class FakeMuDoc:
        def __getitem__(self, idx):
            return FakeMuPage()

        def close(self):
            pass

    fake_pymupdf = types.ModuleType("pymupdf")
    fake_pymupdf.open = lambda path: FakeMuDoc()
    fake_pymupdf.Matrix = lambda *a, **k: None

    ocr_call_count = {"n": 0}

    def fake_image_to_string(image, lang=None, config=None):
        ocr_call_count["n"] += 1
        n = ocr_call_count["n"]
        if n in ocr_failures:
            raise RuntimeError(f"OCR blew up on call {n}")
        return f"ocr text (call {n})"

    fake_pytesseract = types.ModuleType("pytesseract")
    fake_pytesseract.image_to_string = fake_image_to_string

    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)
    monkeypatch.setitem(sys.modules, "pymupdf", fake_pymupdf)
    monkeypatch.setitem(sys.modules, "pytesseract", fake_pytesseract)

    # extract_pdf_text may already be imported (cached) from an earlier
    # test in the session with the real/absent libraries bound — force a
    # fresh import against the fakes above.
    sys.modules.pop("extract_pdf_text", None)
    import extract_pdf_text
    return extract_pdf_text


@pytest.fixture
def fake_pdf_path(tmp_path):
    path = tmp_path / "manual.pdf"
    path.write_bytes(b"not a real pdf, only stat()'d")
    return path


def test_ocr_failure_on_one_page_does_not_block_later_pages(monkeypatch, fake_pdf_path):
    # 3 scanned (no-extractable-text) pages; the OCR call for page 2 fails,
    # but pages 1 and 3 should still get their OCR text (finding #18 — this
    # used to disable OCR for every page after the first failure).
    module = _install_fake_pdf_stack(monkeypatch, page_texts=[None, None, None], ocr_failures={2})
    monkeypatch.setattr(module, "TESSERACT_AVAILABLE", True)

    result = module.extract_pdf_text(fake_pdf_path)

    assert result["status"] == "success"
    assert "ocr text (call 1)" in result["text"]
    assert "ocr text (call 3)" in result["text"]
    assert result["ocr_pages_used"] == [1, 3]  # page 2 excluded — its OCR failed
    assert "ocr_unavailable_reason" not in result


def test_missing_tesseract_binary_skips_ocr_entirely(monkeypatch, fake_pdf_path):
    module = _install_fake_pdf_stack(monkeypatch, page_texts=[None], ocr_failures=set())
    monkeypatch.setattr(module, "TESSERACT_AVAILABLE", False)

    result = module.extract_pdf_text(fake_pdf_path)

    assert result["status"] == "success"
    assert result["ocr_pages_used"] == []
    assert result["ocr_unavailable_reason"] == "tesseract binary not found on PATH"


def test_pages_with_extractable_text_never_trigger_ocr(monkeypatch, fake_pdf_path):
    module = _install_fake_pdf_stack(monkeypatch, page_texts=["real text page 1"], ocr_failures=set())
    monkeypatch.setattr(module, "TESSERACT_AVAILABLE", True)

    result = module.extract_pdf_text(fake_pdf_path)

    assert result["status"] == "success"
    assert "real text page 1" in result["text"]
    assert result["ocr_pages_used"] == []
