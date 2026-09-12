from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from markitdown_desktop.core.secrets import AZURE_KEY, LLM_API_KEY, SecretStore
from markitdown_desktop.core.settings import AppSettings


class OcrMode(StrEnum):
    LOCAL = "local"
    AZURE = "azure"
    LLM = "llm"


DEFAULT_LLM_MODEL = "gpt-4o"


@dataclass(frozen=True)
class OcrConfig:
    mode: OcrMode = OcrMode.LOCAL
    azure_endpoint: str = ""
    azure_key: str = ""
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = DEFAULT_LLM_MODEL

    @property
    def is_ready(self) -> bool:
        if self.mode is OcrMode.AZURE:
            return bool(self.azure_endpoint.strip() and self.azure_key.strip())
        if self.mode is OcrMode.LLM:
            return bool(self.llm_api_key.strip() and self.llm_model.strip())
        return True

    @classmethod
    def from_settings(cls, settings: AppSettings, secrets: SecretStore) -> OcrConfig:
        return cls(
            mode=OcrMode(settings.ocr_mode),
            azure_endpoint=settings.azure_endpoint,
            azure_key=secrets.get(AZURE_KEY) or "",
            llm_base_url=settings.llm_base_url,
            llm_api_key=secrets.get(LLM_API_KEY) or "",
            llm_model=settings.llm_model,
        )
