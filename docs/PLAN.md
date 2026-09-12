# MarkItDown Desktop – Projektplan

Stand: 2026-09-12. Abgestimmt und freigegeben vor Umsetzungsbeginn.

## Ziel

Kleines Desktop-Tool um [Microsoft MarkItDown](https://github.com/microsoft/markitdown):
Datei droppen oder per Finder/Explorer wählen → `<name>.md` entsteht neben der Quelle
(Zielordner änderbar). OCR ist eingebaut. Für macOS und Windows gibt es je einen Installer,
der **alles** mitbringt (Python-Runtime, alle MarkItDown-Pakete, OCR-Engine + Modelle).

## Plattformen

| Plattform | Mindestversion | Architektur | Installer |
|---|---|---|---|
| macOS | 14 (Sonoma) | Apple Silicon (arm64) | `.dmg`, signiert + notarisiert (Developer ID) |
| Windows | 10 (Build 19041) / 11 | x64 | `.msi` (WiX), vorerst unsigniert |

iOS wurde bewusst gestrichen (kein klassischer Installer, kein Python/ONNX-Subprozess im
Sandbox-Modell). Intel-Macs werden nicht unterstützt, weil `onnxruntime` ab 1.30 kein
x86_64-macOS-Wheel mehr liefert.

## Funktionsumfang (MVP)

1. **Eingabe:** Drag & Drop (mehrere Dateien) oder nativer Datei-Dialog. Angenommen werden nur
   von MarkItDown unterstützte Typen (PDF, DOCX, PPTX, XLSX/XLS, Bilder, HTML, CSV/JSON/XML,
   EPUB, ZIP, MSG, Audio). YouTube-URLs werden nicht angeboten.
2. **Ausgabe:** `<name>.md` neben der Quelle (Standard) oder in einem festen Zielordner;
   Einstellung wird gespeichert.
3. **Konflikt:** existiert die `.md` bereits → Nachfrage (Überschreiben / `name (2).md` /
   Überspringen) mit „für alle merken“.
4. **Ablauf:** Konvertierung im Hintergrund-Thread, Fortschritt und Status je Datei, Fehler je
   Datei lesbar, „Im Finder/Explorer zeigen“, Abbrechen.
5. **OCR-Modi** (Erststart-Assistent, A vorausgewählt; jederzeit in den Einstellungen änderbar):
   - **A Lokal (Standard):** RapidOCR (ONNX Runtime), offline, Deutsch + Englisch. Greift bei
     Bilddateien und bei PDF-Seiten ohne Textebene (Erkennung per Textdichte).
   - **B Azure Document Intelligence:** MarkItDowns `docintel_endpoint`; Endpoint + Key,
     Verbindungstest.
   - **C LLM Vision:** offizielles `markitdown-ocr`-Plugin mit OpenAI-kompatiblem Client;
     API-Key, Modell, optional Base-URL, Verbindungstest.
   - Alle drei Modi sind immer installiert; der Installer/Erststart legt nur den Startmodus fest.
   - Zugangsdaten liegen im System-Schlüsselbund (`keyring`).
6. **UI-Sprache:** Deutsch/Englisch nach Systemsprache, in den Einstellungen umschaltbar.

Nicht im MVP (Folgeschritt): lokales OCR für in DOCX/PPTX/XLSX eingebettete Bilder
(Modus C kann das per Plugin bereits), Auto-Update, Explorer/Finder-Kontextmenü.

## Technik

- Python 3.12 (Entwicklung ≥ 3.11), PySide6 (Qt 6), `markitdown[all]` 0.1.7, `markitdown-ocr`,
  `openai`, `rapidocr` + `onnxruntime`, `pypdfium2`, `keyring`, `platformdirs`.
- Paketierung mit Briefcase (`.dmg`, `.msi`); alle Abhängigkeiten als Binary-Wheels verfügbar.
- Tests: pytest + pytest-qt (offscreen); CI auf ubuntu/macos/windows.

```
src/markitdown_desktop/
├── core/        converter (MarkItDown-Service, Zielpfad, Konflikte), worker (QThread),
│                settings (QSettings + keyring), ocr/{local,azure,llm}.py
├── ui/          main_window, drop_zone, settings_dialog, first_run_wizard
├── i18n/        Qt-Übersetzungen de/en
└── resources/   Icon
```

## Meilensteine

| # | Inhalt | Prüfbar durch |
|---|---|---|
| 0 | Repo, Scaffold, CI (Lint/Typen/Tests) grün | CI |
| 1 | Core: Konvertierung, Zielpfad, Konflikte, Tests mit Beispieldateien | `pytest` |
| 2 | GUI: Fenster, Drop, Dialog, Zielordner, Batch, Fortschritt | pytest-qt |
| 3 | OCR A/B/C, Einstellungen, Erststart-Assistent, keyring | Tests (A offline, B/C gemockt) |
| 4 | i18n DE/EN | Übersetzungsabdeckung |
| 5 | Briefcase-Packaging, Release-Workflow, macOS-Signierung/Notarisierung | `.dmg`/`.msi` auf echten Geräten |

## Release-Pipeline und Secrets (Meilenstein 5)

`release.yml` läuft bei Tag `v*` auf `macos-14` (arm64) und `windows-latest`, baut beide
Installer und hängt sie an ein GitHub-Release. Für macOS werden folgende Repository-Secrets
benötigt (Namen werden in Meilenstein 5 final dokumentiert):

- `MACOS_CERTIFICATE_P12` (Base64 des „Developer ID Application“-Zertifikats),
  `MACOS_CERTIFICATE_PASSWORD`
- `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_SPECIFIC_PASSWORD` (für `notarytool`)

Windows bleibt bis zum Vorliegen eines Code-Signing-Zertifikats unsigniert; der
SmartScreen-Hinweis ist in der README dokumentiert.

## Grenzen der Entwicklungsumgebung

Entwicklung und Tests laufen unter Linux (Qt offscreen). Die Installer entstehen ausschließlich
in der CI auf macOS-/Windows-Runnern; die Prüfung der fertigen Installer erfolgt auf echten
Geräten anhand der Checkliste in Meilenstein 5.
