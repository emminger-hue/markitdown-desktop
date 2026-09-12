import shutil
from pathlib import Path

import pytest

from markitdown_desktop.core.converter import (
    SUPPORTED_EXTENSIONS,
    ConflictPolicy,
    ConversionService,
    Status,
    is_supported,
    output_path_for,
    resolve_conflict,
    unique_path,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="module")
def service() -> ConversionService:
    return ConversionService()


def test_output_path_defaults_to_source_directory() -> None:
    src = Path("/data/reports/Q3 report.PDF")
    assert output_path_for(src) == Path("/data/reports/Q3 report.md")
    assert output_path_for(src, Path("/out")) == Path("/out/Q3 report.md")


def test_unique_path_numbers_like_finder(tmp_path: Path) -> None:
    target = tmp_path / "a.md"
    assert unique_path(target) == target
    target.write_text("x")
    assert unique_path(target) == tmp_path / "a (2).md"
    (tmp_path / "a (2).md").write_text("x")
    assert unique_path(target) == tmp_path / "a (3).md"


def test_resolve_conflict_policies(tmp_path: Path) -> None:
    src = tmp_path / "doc.pdf"
    src.write_bytes(b"%PDF")
    existing = tmp_path / "doc.md"
    existing.write_text("old")
    assert resolve_conflict(src, existing, ConflictPolicy.OVERWRITE) == existing
    assert resolve_conflict(src, existing, ConflictPolicy.RENAME) == tmp_path / "doc (2).md"
    assert resolve_conflict(src, existing, ConflictPolicy.SKIP) is None


def test_markdown_source_is_never_overwritten(tmp_path: Path) -> None:
    src = tmp_path / "notes.md"
    src.write_text("# notes")
    assert resolve_conflict(src, output_path_for(src), ConflictPolicy.OVERWRITE) == (
        tmp_path / "notes (2).md"
    )


def test_is_supported_is_case_insensitive() -> None:
    assert is_supported(Path("x.PDF"))
    assert is_supported(Path("x.Docx"))
    assert not is_supported(Path("x.xyz"))
    assert ".tiff" in SUPPORTED_EXTENSIONS


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("sample.pdf", "Textseite"),
        ("sample.docx", "# Beispieldokument"),
        ("sample.pptx", "# Beispielfolie"),
        ("sample.xlsx", "| Äpfel | 12.5 |"),
        ("sample.html", "# Beispiel"),
        ("sample.csv", "| Position | Betrag |"),
    ],
)
def test_converts_fixture_next_to_source(
    service: ConversionService, tmp_path: Path, name: str, expected: str
) -> None:
    src = tmp_path / name
    shutil.copy(FIXTURES / name, src)
    result = service.convert(src)
    assert result.status is Status.OK, result.message
    assert result.output == tmp_path / f"{src.stem}.md"
    assert expected in result.output.read_text(encoding="utf-8")
    assert result.seconds > 0


def test_converts_into_fixed_target_directory(service: ConversionService, tmp_path: Path) -> None:
    src = tmp_path / "sample.docx"
    shutil.copy(FIXTURES / "sample.docx", src)
    out_dir = tmp_path / "out" / "nested"
    result = service.convert(src, target_dir=out_dir)
    assert result.status is Status.OK
    assert result.output == out_dir / "sample.md"
    assert result.output.exists()


def test_scanned_pdf_without_ocr_is_reported_empty(
    service: ConversionService, tmp_path: Path
) -> None:
    src = tmp_path / "scan.pdf"
    shutil.copy(FIXTURES / "scan.pdf", src)
    result = service.convert(src)
    assert result.status is Status.EMPTY
    assert result.output is not None and result.output.exists()


def test_skip_policy_leaves_existing_file_alone(service: ConversionService, tmp_path: Path) -> None:
    src = tmp_path / "sample.csv"
    shutil.copy(FIXTURES / "sample.csv", src)
    existing = tmp_path / "sample.md"
    existing.write_text("keep me", encoding="utf-8")
    result = service.convert(src, policy=ConflictPolicy.SKIP)
    assert result.status is Status.SKIPPED
    assert existing.read_text(encoding="utf-8") == "keep me"


def test_rename_policy_creates_numbered_file(service: ConversionService, tmp_path: Path) -> None:
    src = tmp_path / "sample.csv"
    shutil.copy(FIXTURES / "sample.csv", src)
    (tmp_path / "sample.md").write_text("keep me", encoding="utf-8")
    result = service.convert(src, policy=ConflictPolicy.RENAME)
    assert result.status is Status.OK
    assert result.output == tmp_path / "sample (2).md"


def test_unsupported_and_missing_files(service: ConversionService, tmp_path: Path) -> None:
    src = tmp_path / "unsupported.xyz"
    shutil.copy(FIXTURES / "unsupported.xyz", src)
    assert service.convert(src).status is Status.UNSUPPORTED
    assert service.convert(tmp_path / "missing.pdf").status is Status.ERROR


def test_converter_errors_are_reported_not_raised(tmp_path: Path) -> None:
    class Exploding:
        def convert(self, *_args, **_kwargs):
            raise RuntimeError("boom\nsecond line")

    src = tmp_path / "sample.csv"
    shutil.copy(FIXTURES / "sample.csv", src)
    failing = ConversionService(factory=Exploding)  # type: ignore[arg-type]
    result = failing.convert(src)
    assert result.status is Status.ERROR
    assert result.message == "boom"
    assert not (tmp_path / "sample.md").exists()
