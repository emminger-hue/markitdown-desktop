from __future__ import annotations

from markitdown import MarkItDown

from markitdown_desktop.core.ocr import OcrConfig, OcrMode
from markitdown_desktop.core.ocr.local import LocalOcrConverter

LOCAL_OCR_PRIORITY = -1.0  # before MarkItDown's built-ins (0.0), like markitdown-ocr does


def build_markitdown(config: OcrConfig) -> MarkItDown:
    """Cloud modes need credentials; without them the offline engine is used."""
    if config.mode is OcrMode.AZURE and config.is_ready:
        from azure.core.credentials import AzureKeyCredential

        return MarkItDown(
            docintel_endpoint=config.azure_endpoint.strip(),
            docintel_credential=AzureKeyCredential(config.azure_key.strip()),
        )
    if config.mode is OcrMode.LLM and config.is_ready:
        return MarkItDown(
            enable_plugins=True,
            llm_client=make_llm_client(config, timeout=120.0),
            llm_model=config.llm_model.strip(),
        )
    markitdown = MarkItDown()
    markitdown.register_converter(LocalOcrConverter(), priority=LOCAL_OCR_PRIORITY)
    return markitdown


def make_llm_client(config: OcrConfig, timeout: float):
    from openai import OpenAI

    return OpenAI(
        api_key=config.llm_api_key.strip(),
        base_url=config.llm_base_url.strip() or None,
        timeout=timeout,
        max_retries=1,
    )


def check_azure_connection(endpoint: str, key: str) -> None:
    """Raises with the service's error message if endpoint or key are wrong."""
    from azure.ai.documentintelligence import DocumentIntelligenceAdministrationClient
    from azure.core.credentials import AzureKeyCredential

    client = DocumentIntelligenceAdministrationClient(
        endpoint=endpoint.strip(), credential=AzureKeyCredential(key.strip())
    )
    client.get_resource_details()


def check_llm_connection(config: OcrConfig) -> None:
    """Raises with the provider's error message if key, URL or model are wrong."""
    make_llm_client(config, timeout=15.0).models.retrieve(config.llm_model.strip())
