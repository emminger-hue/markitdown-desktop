import shutil
from pathlib import Path

import pytest

from markitdown_desktop.core.converter import ConversionService, Status
from markitdown_desktop.core.ocr import OcrConfig, OcrMode
from markitdown_desktop.core.ocr.factory import LOCAL_OCR_PRIORITY, build_markitdown
from markitdown_desktop.core.ocr.local import LocalOcrConverter
from markitdown_desktop.core.secrets import AZURE_KEY, LLM_API_KEY, MemorySecretStore
from markitdown_desktop.core.settings import AppSettings

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="module")
def local_service() -> ConversionService:
    return ConversionService(factory=lambda: build_markitdown(OcrConfig(mode=OcrMode.LOCAL)))


def convert(service: ConversionService, name: str, tmp_path: Path) -> str:
    src = tmp_path / name
    shutil.copy(FIXTURES / name, src)
    result = service.convert(src)
    assert result.status is Status.OK, result.message
    assert result.output is not None
    return result.output.read_text(encoding="utf-8")


def test_local_ocr_reads_image(local_service: ConversionService, tmp_path: Path) -> None:
    text = convert(local_service, "sample.png", tmp_path)
    assert "Rechnung Nr. 4711" in text
    assert "Äpfel" in text


def test_local_ocr_reads_scanned_pdf(local_service: ConversionService, tmp_path: Path) -> None:
    text = convert(local_service, "scan.pdf", tmp_path)
    assert "4711" in text
    assert "quick brown fox" in text


def test_pdf_with_text_layer_keeps_builtin_extraction(
    local_service: ConversionService, tmp_path: Path
) -> None:
    text = convert(local_service, "sample.pdf", tmp_path)
    assert "Textseite" in text


def test_local_converter_accepts_images_and_pdfs() -> None:
    from markitdown import StreamInfo

    converter = LocalOcrConverter()
    assert converter.accepts(None, StreamInfo(extension=".TIFF"))  # type: ignore[arg-type]
    assert converter.accepts(None, StreamInfo(mimetype="image/webp"))  # type: ignore[arg-type]
    assert converter.accepts(None, StreamInfo(extension=".pdf"))  # type: ignore[arg-type]
    assert not converter.accepts(None, StreamInfo(extension=".docx"))  # type: ignore[arg-type]


def converter_names(markitdown) -> list[str]:
    return [type(reg.converter).__name__ for reg in markitdown._converters]


def test_factory_local_registers_converter_first() -> None:
    md = build_markitdown(OcrConfig(mode=OcrMode.LOCAL))
    first = md._converters[0]
    assert type(first.converter) is LocalOcrConverter
    assert first.priority == LOCAL_OCR_PRIORITY


def test_factory_azure_uses_document_intelligence() -> None:
    md = build_markitdown(
        OcrConfig(mode=OcrMode.AZURE, azure_endpoint="https://x.example/", azure_key="k")
    )
    assert "DocumentIntelligenceConverter" in converter_names(md)
    assert "LocalOcrConverter" not in converter_names(md)


def test_factory_llm_enables_markitdown_ocr_plugin() -> None:
    md = build_markitdown(OcrConfig(mode=OcrMode.LLM, llm_api_key="sk-test"))
    assert "PdfConverterWithOCR" in converter_names(md)
    assert md._llm_model == "gpt-4o"


def test_factory_falls_back_to_local_without_credentials() -> None:
    md = build_markitdown(OcrConfig(mode=OcrMode.AZURE))
    assert "LocalOcrConverter" in converter_names(md)


def test_config_from_settings_and_secrets(settings: AppSettings) -> None:
    secrets = MemorySecretStore()
    secrets.set(AZURE_KEY, "azure-key")
    secrets.set(LLM_API_KEY, "sk-1")
    settings.ocr_mode = "llm"
    settings.llm_model = "gpt-4.1"
    settings.llm_base_url = "https://proxy.example/v1"
    config = OcrConfig.from_settings(settings, secrets)
    assert config.mode is OcrMode.LLM
    assert config.llm_api_key == "sk-1"
    assert config.azure_key == "azure-key"
    assert config.llm_base_url == "https://proxy.example/v1"
    assert config.is_ready
    assert not OcrConfig(mode=OcrMode.LLM).is_ready
