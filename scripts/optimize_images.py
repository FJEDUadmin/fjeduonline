#!/usr/bin/env python3
"""Batch optimize JPEG files for faster web delivery.

This utility rewrites JPEG images with progressive encoding and optimization,
then keeps the new file only when it is smaller than the original.
"""

from __future__ import annotations

import argparse
import glob
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError


@dataclass
class Stats:
    files_scanned: int = 0
    files_optimized: int = 0
    files_skipped: int = 0
    bytes_before: int = 0
    bytes_after: int = 0


def optimize_file(path: Path, quality: int, min_saved_bytes: int, dry_run: bool) -> tuple[bool, int, int]:
    """Optimize one JPEG and return (optimized, before_bytes, after_bytes)."""
    before = path.stat().st_size
    with Image.open(path) as image:
        if image.format != "JPEG":
            return False, before, before

        # JPEG does not support alpha channel.
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        save_kwargs = {
            "format": "JPEG",
            "quality": quality,
            "optimize": True,
            "progressive": True,
        }
        icc_profile = image.info.get("icc_profile")
        exif = image.info.get("exif")
        if icc_profile:
            save_kwargs["icc_profile"] = icc_profile
        if exif:
            save_kwargs["exif"] = exif

        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".jpg", delete=False) as tmp:
            tmp_name = tmp.name
        try:
            image.save(tmp_name, **save_kwargs)
            after = os.path.getsize(tmp_name)
            if before - after >= min_saved_bytes:
                if not dry_run:
                    os.replace(tmp_name, path)
                else:
                    os.remove(tmp_name)
                return True, before, after

            os.remove(tmp_name)
            return False, before, before
        except Exception:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch optimize JPEG files")
    parser.add_argument(
        "--glob",
        dest="glob_pattern",
        default="*.jpg",
        help="Glob pattern for image files (default: *.jpg)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=95,
        help="JPEG quality for re-encoding (default: 95)",
    )
    parser.add_argument(
        "--min-saved-bytes",
        type=int,
        default=1024,
        help="Only replace files that shrink at least this many bytes (default: 1024)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and report without modifying files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not (1 <= args.quality <= 95):
        raise SystemExit("--quality must be between 1 and 95")
    if args.min_saved_bytes < 0:
        raise SystemExit("--min-saved-bytes must be >= 0")

    paths = sorted(Path(p) for p in glob.glob(args.glob_pattern) if Path(p).is_file())
    stats = Stats(files_scanned=len(paths))

    for path in paths:
        try:
            optimized, before, after = optimize_file(
                path=path,
                quality=args.quality,
                min_saved_bytes=args.min_saved_bytes,
                dry_run=args.dry_run,
            )
            stats.bytes_before += before
            stats.bytes_after += after
            if optimized:
                stats.files_optimized += 1
                print(f"optimized: {path} ({before} -> {after})")
            else:
                stats.files_skipped += 1
        except UnidentifiedImageError:
            stats.files_skipped += 1
            print(f"skipped (not an image): {path}")
        except Exception as exc:  # pragma: no cover - script safety path
            stats.files_skipped += 1
            print(f"skipped (error): {path} ({exc})")

    saved = stats.bytes_before - stats.bytes_after
    pct = (saved / stats.bytes_before * 100) if stats.bytes_before else 0

    print()
    print("Optimization summary")
    print("--------------------")
    print(f"files_scanned:    {stats.files_scanned}")
    print(f"files_optimized:  {stats.files_optimized}")
    print(f"files_skipped:    {stats.files_skipped}")
    print(f"bytes_before:     {stats.bytes_before}")
    print(f"bytes_after:      {stats.bytes_after}")
    print(f"bytes_saved:      {saved}")
    print(f"saved_percent:    {pct:.2f}%")


if __name__ == "__main__":
    main()
