"""Synthetic images only; never use clinical fixtures here."""
import csv
import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from data.duplicates import mark_duplicates
from data.inventory import inspect_image, inventory
from data.pipeline import run
from data.quality import quality_issues


def synthetic_png(path: Path, size=(808, 842), shade=80):
    array = np.full((size[1], size[0], 3), shade, dtype=np.uint8)
    array[10:50, 10:50] = 200
    Image.fromarray(array).save(path, format="PNG")


def test_valid_image_dimensions_and_inventory(tmp_path):
    file = tmp_path / "sample.png"
    synthetic_png(file)
    rows = inventory(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert (row["width_px"], row["height_px"], row["channels"]) == (808, 842, 3)
    assert row["actual_format"] == "PNG"
    assert row["integrity_status"] == "VALID"
    assert row["sha256"] == hashlib.sha256(file.read_bytes()).hexdigest()


def test_corrupt_empty_and_wrong_extension(tmp_path):
    (tmp_path / "broken.png").write_bytes(b"not an image")
    (tmp_path / "empty.png").touch()
    synthetic_png(tmp_path / "wrong.jpg")
    rows = inventory(tmp_path)
    states = {r["filename"]: r["integrity_status"] for r in rows}
    assert states == {"broken.png": "UNREADABLE", "empty.png": "EMPTY", "wrong.jpg": "VALID"}
    issues = quality_issues(rows)
    assert {i["issue_code"] for i in issues} >= {"UNREADABLE", "EMPTY", "EXTENSION_MISMATCH"}


def test_exact_and_visual_duplicate_candidates(tmp_path):
    synthetic_png(tmp_path / "a.png")
    (tmp_path / "b.png").write_bytes((tmp_path / "a.png").read_bytes())
    # Same pixels with different PNG metadata gives a different file hash.
    from PIL.PngImagePlugin import PngInfo
    info = PngInfo()
    info.add_text("test", "synthetic")
    with Image.open(tmp_path / "a.png") as image:
        image.save(tmp_path / "c.png", pnginfo=info)
    rows = inventory(tmp_path)
    pairs = mark_duplicates(rows, tmp_path)
    assert sum(p["kind"] == "EXACT" for p in pairs) == 1
    assert sum(p["kind"] == "VISUAL_CANDIDATE" for p in pairs) == 2
    assert all(r["exact_duplicate"] for r in rows[:2])


def test_missing_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        inventory(tmp_path / "missing")


def test_rerun_preserves_original_and_manual_labels(tmp_path):
    raw = tmp_path / "dataset" / "raw"
    raw.mkdir(parents=True)
    file = raw / "synthetic.png"
    synthetic_png(file)
    before = hashlib.sha256(file.read_bytes()).hexdigest()
    output = tmp_path / "reports"
    first = run(raw, output)
    labels = raw.parent / "metadata" / "clinical_labels.csv"
    with labels.open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    records[0]["reviewed_by"] = "synthetic reviewer"
    with labels.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    second = run(raw, output)
    with labels.open(encoding="utf-8-sig", newline="") as stream:
        final = list(csv.DictReader(stream))
    assert first == second
    assert len(final) == 1
    assert final[0]["reviewed_by"] == "synthetic reviewer"
    assert hashlib.sha256(file.read_bytes()).hexdigest() == before
    assert (output / "summary.json").is_file()
