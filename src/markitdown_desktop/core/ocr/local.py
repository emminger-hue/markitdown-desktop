from __future__ import annotations

import io
import logging
import threading
from typing import Any, BinaryIO

import numpy as np
from markitdown import DocumentConverter, DocumentConverterResult, StreamInfo
from markitdown.converters import PdfConverter
from PIL import Image

IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".gif"})
PDF_MIMETYPES = ("application/pdf", "application/x-pdf")
MIN_TEXT_CHARS_PER_PAGE = 25
RENDER_SCALE = 200 / 72  # 200 dpi is plenty for OCR and keeps memory modest

_engine: Any = None
_engine_lock = threading.Lock()


def get_engine() -> Any:
    """Shared RapidOCR instance; loading the ONNX models takes ~0.5 s, so do it once."""
    global _engine
    with _engine_lock:
        if _engine is None:
            # rapidocr attaches a coloured stderr handler (and resets the level to INFO)
            # in every module that imports its logger, unless a handler is already present.
            logger = logging.getLogger("RapidOCR")
            if not logger.handlers:  # leave it alone when diagnostics configured it already
                logger.addHandler(logging.NullHandler())
                logger.setLevel(logging.WARNING)
            from rapidocr import RapidOCR

            _engine = RapidOCR()
        return _engine


def ocr_image(image: Image.Image, engine: Any | None = None) -> str:
    engine = engine if engine is not None else get_engine()
    bgr = np.ascontiguousarray(np.asarray(image.convert("RGB"))[:, :, ::-1])
    output = engine(bgr)
    lines = output.txts if output is not None and output.txts else ()
    return "\n".join(line.strip() for line in lines if line.strip())


class LocalOcrConverter(DocumentConverter):
    """Offline OCR for image files and for PDF pages that have no text layer.

    PDFs whose pages all carry text are delegated unchanged to MarkItDown's own
    PdfConverter so tables/forms keep its richer extraction.
    """

    def __init__(self, engine_factory=get_engine) -> None:
        super().__init__()
        self._engine_factory = engine_factory
        self._pdf_fallback = PdfConverter()

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any) -> bool:
        extension = (stream_info.extension or "").lower()
        mimetype = (stream_info.mimetype or "").lower()
        return (
            extension in IMAGE_EXTENSIONS
            or extension == ".pdf"
            or mimetype.startswith("image/")
            or mimetype in PDF_MIMETYPES
        )

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> DocumentConverterResult:
        data = file_stream.read()
        if data.startswith(b"%PDF") or (stream_info.extension or "").lower() == ".pdf":
            return self._convert_pdf(data, file_stream, stream_info, **kwargs)
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            return DocumentConverterResult(markdown=ocr_image(image, self._engine_factory()))

    def _convert_pdf(
        self, data: bytes, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> DocumentConverterResult:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(data)
        try:
            texts = [page.get_textpage().get_text_range() for page in pdf]
            needs_ocr = {
                i for i, text in enumerate(texts) if len(text.strip()) < MIN_TEXT_CHARS_PER_PAGE
            }
            if not needs_ocr:
                file_stream.seek(0)
                return self._pdf_fallback.convert(file_stream, stream_info, **kwargs)

            engine = self._engine_factory()
            chunks: list[str] = []
            for index, page in enumerate(pdf):
                if index in needs_ocr:
                    text = ocr_image(page.render(scale=RENDER_SCALE).to_pil(), engine)
                else:
                    text = texts[index]
                if text.strip():
                    chunks.append(text.strip())
            return DocumentConverterResult(markdown="\n\n".join(chunks))
        finally:
            pdf.close()
