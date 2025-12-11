"""Utilities for batch renaming operations"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Callable, Iterable, Tuple

RenameBuilder = Callable[[int, Path, Path], str | None]


def two_phase_rename(
    images: Iterable[Path],
    build_name: RenameBuilder,
    current_path: Path | None = None,
) -> Tuple[int, int, int, Path | None]:
    """Rename images with a temporary pass to avoid collisions.

    Returns (renamed, skipped, failed, replacement).
    """
    temp_paths: list[tuple[Path, Path]] = []
    for idx, img in enumerate(images, start=1):
        tmp = img.with_name(f"__rvtmp__{uuid.uuid4().hex}__{img.name}")
        try:
            img.rename(tmp)
            temp_paths.append((tmp, img))
        except Exception:
            continue

    renamed = skipped = failed = 0
    replacement: Path | None = None

    for idx, (tmp_path, original) in enumerate(temp_paths, start=1):
        new_name = build_name(idx, tmp_path, original)
        if not new_name:
            skipped += 1
            try:
                tmp_path.rename(original)
            except Exception:
                failed += 1
            continue
        dest = tmp_path.with_name(new_name)
        try:
            if dest.exists():
                skipped += 1
                tmp_path.rename(original)
                continue
            tmp_path.rename(dest)
            if current_path and original.resolve() == current_path.resolve():
                replacement = dest
            renamed += 1
        except Exception:
            failed += 1
            try:
                tmp_path.rename(original)
            except Exception:
                pass

    return renamed, skipped, failed, replacement
