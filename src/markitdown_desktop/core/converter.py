from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from markitdown import MarkItDown, UnsupportedFormatException

BUILTIN_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".docx",
        ".pptx",
        ".xlsx",
        ".xls",
        ".csv",
        ".json",
        ".jsonl",
        ".txt",
        ".text",
        ".md",
        ".markdown",
        ".html",
        ".htm",
        ".epub",
        ".zip",
        ".msg",
        ".ipynb",
        ".wav",
        ".mp3",
        ".m4a",
        ".mp4",
        ".jpg",
        ".jpeg",
        ".png",
    }
)
OCR_IMAGE_EXTENSIONS = frozenset({".bmp", ".tif", ".tiff", ".webp", ".gif"})
SUPPORTED_EXTENSIONS = BUILTIN_EXTENSIONS | OCR_IMAGE_EXTENSIONS


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def expand_paths(paths: Iterable[Path]) -> list[Path]:
    """Files as given; folders recursively, but only their supported, non-hidden files."""
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(
                child
                for child in sorted(path.rglob("*"))
                if child.is_file() and is_supported(child) and not child.name.startswith(".")
            )
        elif path.is_file():
            files.append(path)
    return list(dict.fromkeys(files))


class ConflictPolicy(StrEnum):
    OVERWRITE = "overwrite"
    RENAME = "rename"
    SKIP = "skip"


class Status(StrEnum):
    OK = "ok"
    EMPTY = "empty"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


@dataclass(frozen=True)
class ConversionResult:
    source: Path
    output: Path | None
    status: Status
    message: str = ""
    seconds: float = 0.0

    @property
    def succeeded(self) -> bool:
        return self.status in (Status.OK, Status.EMPTY)


def output_path_for(source: Path, target_dir: Path | None = None) -> Path:
    directory = target_dir if target_dir is not None else source.parent
    return directory / f"{source.stem}.md"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def resolve_conflict(source: Path, candidate: Path, policy: ConflictPolicy) -> Path | None:
    if candidate.resolve() == source.resolve():
        # Never overwrite the file we are converting (e.g. notes.md -> notes.md).
        return unique_path(candidate)
    if not candidate.exists():
        return candidate
    if policy is ConflictPolicy.OVERWRITE:
        return candidate
    if policy is ConflictPolicy.RENAME:
        return unique_path(candidate)
    return None


MarkItDownFactory = Callable[[], MarkItDown]


class ConversionService:
    def __init__(self, factory: MarkItDownFactory | None = None) -> None:
        self._factory: MarkItDownFactory = factory or MarkItDown
        self._markitdown: MarkItDown | None = None

    @property
    def markitdown(self) -> MarkItDown:
        if self._markitdown is None:
            self._markitdown = self._factory()
        return self._markitdown

    def reset(self, factory: MarkItDownFactory | None = None) -> None:
        if factory is not None:
            self._factory = factory
        self._markitdown = None

    def convert(
        self,
        source: Path,
        target_dir: Path | None = None,
        policy: ConflictPolicy = ConflictPolicy.RENAME,
    ) -> ConversionResult:
        started = time.perf_counter()
        source = Path(source)
        if not source.is_file():
            return ConversionResult(source, None, Status.ERROR, "File not found")
        if not is_supported(source):
            return ConversionResult(source, None, Status.UNSUPPORTED, source.suffix)

        output = resolve_conflict(source, output_path_for(source, target_dir), policy)
        if output is None:
            return ConversionResult(source, output_path_for(source, target_dir), Status.SKIPPED)

        try:
            markdown = self.markitdown.convert(str(source)).markdown
        except UnsupportedFormatException as exc:
            return ConversionResult(source, None, Status.UNSUPPORTED, _short(exc))
        except Exception as exc:
            return ConversionResult(source, None, Status.ERROR, _short(exc))

        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(markdown, encoding="utf-8")
        except OSError as exc:
            return ConversionResult(source, output, Status.ERROR, _short(exc))

        status = Status.OK if markdown.strip() else Status.EMPTY
        return ConversionResult(source, output, status, seconds=time.perf_counter() - started)


def _short(exc: BaseException) -> str:
    text = str(exc).strip() or type(exc).__name__
    first_line = text.splitlines()[0]
    return first_line if len(first_line) <= 300 else first_line[:297] + "..."
