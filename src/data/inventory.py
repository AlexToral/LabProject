"""Read-only image inventory. Paths are relative to the input directory."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

FIELDS = [
    "image_id", "filename", "relative_path", "extension", "actual_format",
    "width_px", "height_px", "channels", "color_mode", "size_bytes", "sha256",
    "integrity_status", "aspect_ratio", "intensity_mean", "intensity_std",
    "exact_duplicate", "possible_visual_duplicate", "anonymization_status",
    "manual_review_status", "png_text_metadata_count", "phash",
]
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_image(path: Path, root: Path) -> dict:
    relative = path.relative_to(root).as_posix()
    row = dict.fromkeys(FIELDS, "")
    row.update(
        image_id="IMG-" + hashlib.sha256(relative.encode("utf-8")).hexdigest()[:16],
        filename=path.name, relative_path=relative, extension=path.suffix.lower(),
        size_bytes=path.stat().st_size, anonymization_status="UNVERIFIED",
        manual_review_status="PENDING", exact_duplicate=False,
        possible_visual_duplicate=False,
    )
    row["sha256"] = sha256_file(path)
    if row["size_bytes"] == 0:
        row["integrity_status"] = "EMPTY"
        return row
    try:
        with Image.open(path) as image:
            row["actual_format"] = image.format or ""
            image.verify()
        with Image.open(path) as image:
            image.load()
            row["width_px"], row["height_px"] = image.size
            row["color_mode"] = image.mode
            row["channels"] = len(image.getbands())
            row["aspect_ratio"] = round(image.width / image.height, 6)
            row["png_text_metadata_count"] = len(getattr(image, "text", {}))
            gray = np.asarray(image.convert("L"), dtype=np.uint8)
            row["intensity_mean"] = round(float(gray.mean()), 4)
            row["intensity_std"] = round(float(gray.std()), 4)
            row["integrity_status"] = "VALID"
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        row["integrity_status"] = "UNREADABLE"
    return row


def inventory(input_dir: Path) -> list[dict]:
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    files = sorted(
        (p for p in input_dir.rglob("*") if p.is_file()),
        key=lambda p: p.relative_to(input_dir).as_posix().casefold(),
    )
    return [inspect_image(path, input_dir) for path in files]
