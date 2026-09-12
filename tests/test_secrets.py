import keyring
import keyring.backend
import pytest

from markitdown_desktop.core.secrets import KeyringSecretStore, MemorySecretStore, SecretStoreError


class DictBackend(keyring.backend.KeyringBackend):
    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self.data: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self.data.get((service, username))

    def set_password(self, service, username, password):
        self.data[(service, username)] = password

    def delete_password(self, service, username):
        if (service, username) not in self.data:
            raise keyring.errors.PasswordDeleteError(username)
        del self.data[(service, username)]


@pytest.fixture
def dict_backend():
    previous = keyring.get_keyring()
    backend = DictBackend()
    keyring.set_keyring(backend)
    yield backend
    keyring.set_keyring(previous)


def test_memory_store_roundtrip() -> None:
    store = MemorySecretStore()
    assert store.get("k") is None
    store.set("k", "v")
    assert store.get("k") == "v"
    store.delete("k")
    store.delete("k")
    assert store.get("k") is None


def test_keyring_store_uses_backend(dict_backend: DictBackend) -> None:
    store = KeyringSecretStore(service="test-service")
    store.set("api", "secret")
    assert dict_backend.data[("test-service", "api")] == "secret"
    assert store.get("api") == "secret"
    store.delete("api")
    store.delete("api")  # deleting twice is fine
    assert store.get("api") is None


def test_keyring_failure_is_wrapped() -> None:
    from keyring.backends import fail

    previous = keyring.get_keyring()
    keyring.set_keyring(fail.Keyring())
    try:
        with pytest.raises(SecretStoreError):
            KeyringSecretStore().set("x", "y")
    finally:
        keyring.set_keyring(previous)
