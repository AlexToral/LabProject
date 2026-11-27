"""Aggregate-only plots and cautiously named visual review candidates."""
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def visual_features(rows: list[dict], root: Path) -> list[dict]:
    """Screen for colored pixels and likely layout; clinical interpretation remains manual."""
    result = []
    for row in rows:
        if row["integrity_status"] != "VALID":
            continue
        with Image.open(root / row["relative_path"]) as image:
            rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
        maximum = rgb.max(axis=2).astype(np.int16)
        minimum = rgb.min(axis=2).astype(np.int16)
        colored = (maximum - minimum > 45) & (maximum > 65)
        # A screenshot may have a color UI even without color Doppler.
        color_fraction = float(colored.mean())
        top = rgb[:max(1, rgb.shape[0] // 6)]
        top_bright_fraction = float((top.mean(axis=2) > 150).mean())
        result.append({"image_id": row["image_id"],
                       "color_pixel_fraction": round(color_fraction, 5),
                       "top_band_bright_fraction": round(top_bright_fraction, 5),
                       "color_overlay_candidate": color_fraction >= 0.002,
                       "text_overlay_review": "PENDING",
                       "panel_count_review": "PENDING",
                       "spectral_review": "PENDING",
                       "calibration_review": "PENDING"})
    return result


def make_plots(rows: list[dict], output: Path) -> None:
    valid = [row for row in rows if row["integrity_status"] == "VALID"]
    counts = Counter(f"{row['width_px']}×{row['height_px']}" for row in valid)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(list(counts), list(counts.values()))
    ax.set(title="Distribución de resoluciones", xlabel="Píxeles", ylabel="Imágenes")
    fig.tight_layout()
    fig.savefig(output / "resolution_distribution.png", dpi=150)
    plt.close(fig)

    for values, filename, title, xlabel in [
        ([row["size_bytes"] / 1024 for row in rows], "file_size_distribution.png",
         "Distribución de tamaños", "KiB"),
        ([row["intensity_mean"] for row in valid], "intensity_distribution.png",
         "Distribución de intensidad media", "Intensidad 0–255"),
    ]:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(values, bins=min(20, max(1, len(values))))
        ax.set(title=title, xlabel=xlabel, ylabel="Imágenes")
        fig.tight_layout()
        fig.savefig(output / filename, dpi=150)
        plt.close(fig)
