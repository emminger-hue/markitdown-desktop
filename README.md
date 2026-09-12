# MarkItDown Desktop

A small desktop app around [Microsoft MarkItDown](https://github.com/microsoft/markitdown):
drop a file onto the window (or pick it with Finder / Explorer) and get a Markdown file with
the same name next to the source. OCR for scanned PDFs and images is built in.

**Platforms:** macOS 14+ (Apple Silicon) and Windows 10/11 (x64). Each platform gets a
self-contained installer — no Python, no packages, nothing else to install.

> Status: in development. See [`docs/PLAN.md`](docs/PLAN.md) (German) for the agreed plan
> and [`docs/DECISIONS.md`](docs/DECISIONS.md) for the decision log.

## Features

- Drag & drop one or many files, or choose them with the native file dialog.
- Output `<name>.md` is written next to the source by default; a fixed target folder can be
  set instead. Existing files: ask / overwrite / rename / skip.
- Everything MarkItDown supports: PDF, Word, PowerPoint, Excel, images, HTML, CSV/JSON/XML,
  EPUB, ZIP, Outlook `.msg`, audio.
- Three OCR modes, chosen on first launch and changeable any time in *Settings*:
  - **A – Local (default):** [RapidOCR](https://github.com/RapidAI/RapidOCR) on ONNX Runtime,
    fully offline, German + English. Used for image files and for PDF pages without a text
    layer.
  - **B – Azure Document Intelligence:** MarkItDown's built-in `docintel_endpoint` support.
    Needs an Azure resource, endpoint and key.
  - **C – LLM Vision:** the official [`markitdown-ocr`](https://pypi.org/project/markitdown-ocr/)
    plugin with any OpenAI-compatible endpoint. Needs an API key.
- API keys are stored in the OS credential store (macOS Keychain / Windows Credential Manager),
  never in plain text.
- UI in German and English (follows the system language, switchable in *Settings*).

## Install

Installers are attached to each [GitHub release](https://github.com/emminger-hue/markitdown-desktop/releases):

- **macOS:** `MarkItDown Desktop-<version>.dmg` — signed and notarized. Drag the app to
  *Applications*.
- **Windows:** `MarkItDown Desktop-<version>.msi` — currently **not code-signed**, so
  SmartScreen shows *"Windows protected your PC"*. Click *More info → Run anyway*.

## Development

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m markitdown_desktop        # run the app
pytest                              # tests (Qt runs offscreen)
ruff check . && ruff format .       # lint / format
mypy src                            # type check
```

Translations live in `src/markitdown_desktop/i18n/` (English is the source language). After
changing UI strings:

```bash
pyside6-lupdate -no-obsolete -source-language en -target-language de $(find src -name "*.py") \
    -ts src/markitdown_desktop/i18n/markitdown_desktop_de.ts   # then translate in Qt Linguist
pyside6-lrelease src/markitdown_desktop/i18n/markitdown_desktop_de.ts \
    -qm src/markitdown_desktop/i18n/markitdown_desktop_de.qm    # commit both .ts and .qm
```

Installers are built with [Briefcase](https://briefcase.beeware.org):

```bash
briefcase create && briefcase build && briefcase package   # on the target OS
```

## Releasing

`.github/workflows/release.yml` builds both installers on GitHub-hosted macOS (Apple Silicon)
and Windows runners, runs the bundled app once in `--self-test` mode (converts a scanned PDF
with the offline OCR engine) and, for `v*` tags, attaches the installers to a GitHub release.
It can also be started manually from the *Actions* tab to test-build without a release.

1. Bump `version` in `pyproject.toml` (both `[project]` and `[tool.briefcase]`) and
   `src/markitdown_desktop/__init__.py`.
2. `git tag v0.1.0 && git push origin v0.1.0`.

### macOS signing secrets

Without these the workflow still succeeds but produces an ad-hoc signed, unnotarized DMG that
Gatekeeper blocks on other Macs. Add them under *Settings → Secrets and variables → Actions*:

| Secret | Value |
|---|---|
| `MACOS_CERTIFICATE_P12` | Base64 of the *Developer ID Application* certificate exported as `.p12`: `base64 -i cert.p12 \| pbcopy` |
| `MACOS_CERTIFICATE_PASSWORD` | Password chosen when exporting the `.p12` |
| `MACOS_SIGNING_IDENTITY` | Certificate name, e.g. `Developer ID Application: Jane Doe (ABCDE12345)` |
| `APPLE_ID` | Apple ID e-mail of the developer account |
| `APPLE_TEAM_ID` | 10-character team ID |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password created at appleid.apple.com (for `notarytool`) |

Windows builds are unsigned until a code-signing certificate is available; Briefcase supports
`briefcase package windows --identity <thumbprint>` once one is installed on the runner.

### Manual test checklist (per installer)

- Install from the DMG / MSI on a clean machine; the app starts without any additional setup.
- First launch shows the OCR-mode dialog with *Local OCR* preselected; *Continue* opens the main window.
- Drop `tests/fixtures/scan.pdf` – result is *Done* and `scan.md` contains "Rechnung Nr. 4711".
- Drop `sample.docx`, `sample.xlsx`, `sample.png` and a folder – all convert next to the source.
- Switch to *Save to folder*, pick a folder, convert again – output lands there.
- Drop a file whose `.md` exists – the overwrite / keep both / skip dialog appears; *Remember* sticks.
- *Settings…* → change language to the other one → restart → UI language changed.
- Settings → Azure / LLM mode with real credentials → *Test connection* succeeds → a scan converts.
- macOS only: the app opens without a Gatekeeper warning (signed + notarized build).

## Third-party licenses

MarkItDown (MIT), PySide6 / Qt (LGPL-3.0, dynamically linked), RapidOCR (Apache-2.0),
ONNX Runtime (MIT), pypdfium2 / PDFium (Apache-2.0 / BSD-3-Clause). The bundled installers
ship these components unchanged; their license texts are included in the app bundle.

## License

MIT — see [`LICENSE`](LICENSE).
