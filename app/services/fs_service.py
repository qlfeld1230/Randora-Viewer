"""Filesystem helpers for listing image files in a folder."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

# Common image extensions we consider valid.
IMAGE_EXTENSIONS: set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".webp",
    ".tif",
    ".tiff",
}


def _normalize_extensions(extensions: Sequence[str] | None) -> set[str]:
    """Return a normalized, lowercase extension set (including leading dots)."""
    if extensions is None:
        return IMAGE_EXTENSIONS
    return {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}


def iter_image_files(
    folder: str | Path,
    recursive: bool = False,
    extensions: Sequence[str] | None = None,
) -> Iterable[Path]:
    """Yield image files inside ``folder``.

    Skips unreadable entries instead of failing the whole traversal.
    """
    base = Path(folder).expanduser()
    if not base.is_dir():
        raise ValueError(f"Not a directory: {base}")

    allowed = _normalize_extensions(extensions)
    iterator = base.rglob("*") if recursive else base.iterdir()

    for entry in iterator:
        try:
            if entry.is_file() and entry.suffix.lower() in allowed:
                yield entry
        except OSError:
            # Skip entries we cannot access
            continue


def list_images(
    folder: str | Path,
    recursive: bool = False,
    extensions: Sequence[str] | None = None,
) -> list[Path]:
    """Collect image files inside ``folder`` as a sorted list."""
    return sorted(iter_image_files(folder, recursive=recursive, extensions=extensions))
