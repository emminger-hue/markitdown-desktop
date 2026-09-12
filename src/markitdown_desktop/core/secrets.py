from __future__ import annotations

from typing import Protocol

from markitdown_desktop import APP_NAME


class SecretStoreError(RuntimeError):
    """The OS credential store refused the operation (no backend, locked keychain, ...)."""


class SecretStore(Protocol):
    def get(self, name: str) -> str | None: ...

    def set(self, name: str, value: str) -> None: ...

    def delete(self, name: str) -> None: ...


class MemorySecretStore:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def get(self, name: str) -> str | None:
        return self._values.get(name)

    def set(self, name: str, value: str) -> None:
        self._values[name] = value

    def delete(self, name: str) -> None:
        self._values.pop(name, None)


class KeyringSecretStore:
    """macOS Keychain / Windows Credential Manager via the `keyring` package."""

    def __init__(self, service: str = APP_NAME) -> None:
        self._service = service

    def get(self, name: str) -> str | None:
        import keyring

        try:
            return keyring.get_password(self._service, name)
        except Exception as exc:
            raise SecretStoreError(str(exc)) from exc

    def set(self, name: str, value: str) -> None:
        import keyring

        try:
            keyring.set_password(self._service, name, value)
        except Exception as exc:
            raise SecretStoreError(str(exc)) from exc

    def delete(self, name: str) -> None:
        import keyring
        from keyring.errors import PasswordDeleteError

        try:
            keyring.delete_password(self._service, name)
        except PasswordDeleteError:
            return
        except Exception as exc:
            raise SecretStoreError(str(exc)) from exc


AZURE_KEY = "azure_document_intelligence_key"
LLM_API_KEY = "llm_api_key"
