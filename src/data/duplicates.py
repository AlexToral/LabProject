"""Exact and perceptual duplicate candidates; neither implies clinical identity."""
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def phash(path: Path) -> int:
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L").resize((32, 32)), dtype=np.float32)
    low = cv2.dct(gray)[:8, :8].flatten()
    median = np.median(low[1:])
    return sum(int(value > median) << bit for bit, value in enumerate(low))


def mark_duplicates(rows: list[dict], root: Path, threshold: int = 6) -> list[dict]:
    pairs = []
    by_hash = defaultdict(list)
    valid = []
    for row in rows:
        by_hash[row["sha256"]].append(row)
        if row["integrity_status"] == "VALID":
            row["phash"] = f"{phash(root / row['relative_path']):016x}"
            valid.append(row)
    for group in by_hash.values():
        if len(group) > 1:
            for row in group:
                row["exact_duplicate"] = True
            for left_index in range(len(group)):
                for right_index in range(left_index + 1, len(group)):
                    pairs.append(_pair(group[left_index], group[right_index], "EXACT", 0))
    for left_index, left in enumerate(valid):
        for right in valid[left_index + 1:]:
            if left["sha256"] == right["sha256"]:
                continue
            distance = (int(left["phash"], 16) ^ int(right["phash"], 16)).bit_count()
            if distance <= threshold:
                left["possible_visual_duplicate"] = True
                right["possible_visual_duplicate"] = True
                pairs.append(_pair(left, right, "VISUAL_CANDIDATE", distance))
    return pairs


def _pair(left: dict, right: dict, kind: str, distance: int) -> dict:
    return {"image_id_a": left["image_id"], "image_id_b": right["image_id"],
            "kind": kind, "phash_distance": distance}
