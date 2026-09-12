import xml.etree.ElementTree as ET

from PySide6.QtCore import QCoreApplication

from markitdown_desktop.core.i18n import (
    SUPPORTED_LANGUAGES,
    TRANSLATIONS_DIR,
    install_translators,
    resolve_language,
)


def test_resolve_language_prefers_explicit_setting() -> None:
    assert resolve_language("de") == "de"
    assert resolve_language("en") == "en"
    assert resolve_language("system") in SUPPORTED_LANGUAGES
    assert resolve_language("") in SUPPORTED_LANGUAGES


def _is_translated(message: ET.Element) -> bool:
    translation = message.find("translation")
    if translation is None or translation.get("type") == "unfinished":
        return False
    texts = [translation.text, *(form.text for form in translation.findall("numerusform"))]
    return any(text and text.strip() for text in texts)


def test_german_catalogue_is_complete() -> None:
    root = ET.parse(TRANSLATIONS_DIR / "markitdown_desktop_de.ts").getroot()
    untranslated = [
        message.findtext("source")
        for context in root.findall("context")
        for message in context.findall("message")
        if not _is_translated(message)
    ]
    assert untranslated == []


def test_compiled_german_catalogue_translates(qapp) -> None:
    app = QCoreApplication.instance()
    assert app is not None
    installed = install_translators(app, "de")
    try:
        assert len(installed) == 2, "expected Qt base + app catalogue"
        assert QCoreApplication.translate("MainWindow", "Settings…") == "Einstellungen…"
        assert QCoreApplication.translate("DropZone", "Drop files here") == "Dateien hier ablegen"
        plural = QCoreApplication.translate(
            "MainWindow", "%n Markdown file(s) already exist at the target location.", None, 2
        )
        assert plural == "2 Markdown-Dateien existieren am Zielort bereits."
    finally:
        for translator in installed:
            app.removeTranslator(translator)
    assert QCoreApplication.translate("MainWindow", "Settings…") == "Settings…"


def test_english_installs_nothing(qapp) -> None:
    app = QCoreApplication.instance()
    assert app is not None
    assert install_translators(app, "en") == []
