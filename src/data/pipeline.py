"""Reproducible, read-only processing of source images."""
from __future__ import annotations

import csv
import json
import logging
from collections import Counter
from pathlib import Path

import pandas as pd

from .duplicates import mark_duplicates
from .exploration import make_plots, visual_features
from .inventory import FIELDS, inventory, sha256_file
from .quality import issue_counts, quality_issues

LOG = logging.getLogger(__name__)
LABEL_FIELDS = ["image_id", "patient_id", "study_id", "laterality", "vessel", "modality",
                "arm_position_deg", "compression_site", "diameter_mm", "flow_velocity_cm_s",
                "flow_present", "thrombosis_present", "clinical_class", "annotation_status",
                "reviewed_by", "notes"]
REVIEW_FIELDS = ["image_id", "review_status", "identifier_visible", "identifier_region_px",
                 "panel_layout", "modality_observed", "calibration_visible", "measurement_visible",
                 "reviewer_code"]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def update_labels(path: Path, rows: list[dict]) -> None:
    existing = {}
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != LABEL_FIELDS:
                raise ValueError("Existing clinical_labels.csv has an unexpected schema")
            existing = {record["image_id"]: record for record in reader}
    for row in rows:
        existing.setdefault(row["image_id"], {
            **dict.fromkeys(LABEL_FIELDS, ""), "image_id": row["image_id"],
            "modality": "UNKNOWN", "clinical_class": "UNKNOWN",
            "annotation_status": "PENDING",
        })
    # Keep existing annotations, including rows for an image temporarily missing.
    write_csv(path, [existing[key] for key in sorted(existing)], LABEL_FIELDS)


def update_manual_review(path: Path, rows: list[dict]) -> list[dict]:
    existing = {}
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != REVIEW_FIELDS:
                raise ValueError("Existing manual_visual_review.csv has an unexpected schema")
            existing = {record["image_id"]: record for record in reader}
    for row in rows:
        existing.setdefault(row["image_id"], {
            **dict.fromkeys(REVIEW_FIELDS, ""), "image_id": row["image_id"],
            "review_status": "PENDING", "identifier_visible": "UNKNOWN",
            "panel_layout": "UNKNOWN", "modality_observed": "UNKNOWN",
            "calibration_visible": "UNKNOWN", "measurement_visible": "UNKNOWN",
        })
    ordered = [existing[key] for key in sorted(existing)]
    write_csv(path, ordered, REVIEW_FIELDS)
    return ordered


def _distribution(series) -> dict:
    return {str(key): int(value) for key, value in series.value_counts(dropna=False).sort_index().items()}


def summarize(rows: list[dict], pairs: list[dict], issues: list[dict], features: list[dict], reviews: list[dict]) -> dict:
    df = pd.DataFrame(rows)
    valid = df[df["integrity_status"] == "VALID"]
    resolutions = Counter(f"{row['width_px']}x{row['height_px']}" for row in rows
                          if row["integrity_status"] == "VALID")
    def stats(column):
        series = pd.to_numeric(valid[column], errors="coerce")
        if series.empty:
            return {"min": None, "median": None, "max": None}
        return {"min": round(float(series.min()), 4),
                "median": round(float(series.median()), 4),
                "max": round(float(series.max()), 4)}
    return {
        "total_files": len(rows), "valid_images": len(valid), "invalid_images": len(rows) - len(valid),
        "resolutions": dict(sorted(resolutions.items())),
        "extensions": _distribution(df["extension"]),
        "actual_formats": _distribution(valid["actual_format"]),
        "channels": _distribution(valid["channels"]),
        "color_modes": _distribution(valid["color_mode"]),
        "file_size_bytes": stats("size_bytes"),
        "aspect_ratio": stats("aspect_ratio"),
        "intensity_mean": stats("intensity_mean"),
        "intensity_std": stats("intensity_std"),
        "exact_duplicate_pairs": sum(p["kind"] == "EXACT" for p in pairs),
        "visual_candidate_pairs": sum(p["kind"] == "VISUAL_CANDIDATE" for p in pairs),
        "exact_duplicate_images": sum(bool(r["exact_duplicate"]) for r in rows),
        "visual_candidate_images": sum(bool(r["possible_visual_duplicate"]) for r in rows),
        "issues": issue_counts(issues),
        "images_with_png_text_metadata": sum(int(r["png_text_metadata_count"] or 0) > 0 for r in rows),
        "color_overlay_candidates": sum(bool(f["color_overlay_candidate"]) for f in features),
        "preliminary_screened_images": sum(r["review_status"] == "PRELIMINARY_SCREENED" for r in reviews),
        "visible_identifier_screening_flags": sum(r["review_status"] == "PRELIMINARY_SCREENED" and r["identifier_visible"] == "TRUE" for r in reviews),
        "formally_reviewed_images": sum(r["review_status"] == "REVIEWED" for r in reviews),
        "observed_panel_layouts": dict(sorted(Counter(r["panel_layout"] for r in reviews if r["review_status"] in {"PRELIMINARY_SCREENED", "REVIEWED"}).items())),
        "observed_modalities": dict(sorted(Counter(r["modality_observed"] for r in reviews if r["review_status"] in {"PRELIMINARY_SCREENED", "REVIEWED"}).items())),
        "observed_calibration_images": sum(r["review_status"] in {"PRELIMINARY_SCREENED", "REVIEWED"} and r["calibration_visible"] == "TRUE" for r in reviews),
        "observed_measurement_images": sum(r["review_status"] in {"PRELIMINARY_SCREENED", "REVIEWED"} and r["measurement_visible"] == "TRUE" for r in reviews),
    }


def write_report(path: Path, summary: dict, input_dir: Path) -> None:
    resolutions = ", ".join(f"{k}: {v}" for k, v in summary["resolutions"].items()) or "ninguna"
    issues = ", ".join(f"{k}: {v}" for k, v in summary["issues"].items()) or "ninguna"
    report = f"""# Informe de calidad de datos

## Resumen ejecutivo

Se inspeccionaron {summary['total_files']} archivos en `{input_dir.as_posix()}`: {summary['valid_images']} imágenes válidas y {summary['invalid_images']} inválidas. Estas cifras cuentan archivos, no pacientes ni estudios.
Los SHA-256 de los {summary['total_files']} archivos originales coincidieron antes y después del procesamiento.

## Metodología

Lectura local con Pillow (`verify` y decodificación completa), SHA-256 sobre los bytes originales, estadísticas en escala de grises, pHash DCT de 64 bits con distancia de Hamming ≤ 6 como señal de revisión y muestreo de color sin clasificación clínica. Los umbrales de intensidad y contraste son indicadores de revisión. Se preservaron los originales.

## Inventario

El inventario detallado se conserva fuera de Git en `dataset/metadata/image_inventory.csv` bajo la carpeta del conjunto de datos. Identificadores internos derivados de rutas relativas; no representan pacientes. Distribución de extensiones: {summary['extensions']}. Formatos reales: {summary['actual_formats']}.

## Resultados de calidad

Resoluciones: {resolutions}. Canales: {summary['channels']}. Modos: {summary['color_modes']}. Tamaño en bytes (mínimo, mediana, máximo): {summary['file_size_bytes']}. Relación de aspecto: {summary['aspect_ratio']}. Intensidad media: {summary['intensity_mean']}. Alertas: {issues}.

Duplicados exactos: {summary['exact_duplicate_pairs']} pares ({summary['exact_duplicate_images']} imágenes señaladas). Posibles duplicados visuales: {summary['visual_candidate_pairs']} pares ({summary['visual_candidate_images']} imágenes señaladas). Un par visual puede ser una maniobra o medición distinta y requiere revisión humana.

## Distribución de formatos y composición visual

El conteo de píxeles con color produjo {summary['color_overlay_candidates']} candidatos a superposición cromática. Esto no confirma Doppler color: también puede proceder de la interfaz del ecógrafo. Se visualizaron preliminarmente {summary['preliminary_screened_images']} imágenes de muestra por el asistente; {summary['formally_reviewed_images']} imágenes tienen revisión formal documentada. Distribución de diseños observados en esa muestra: {summary['observed_panel_layouts']}. Modalidades visuales observadas: {summary['observed_modalities']}. Escalas visibles en {summary['observed_calibration_images']} muestras y mediciones visibles en {summary['observed_measurement_images']}. Estas observaciones no se extrapolan a todo el conjunto ni sustituyen revisión clínica.

## Riesgos de privacidad

{summary['images_with_png_text_metadata']} archivos contienen entradas de texto PNG. La ausencia de entradas de texto no confirma anonimización. En {summary['visible_identifier_screening_flags']} de {summary['preliminary_screened_images']} muestras visualizadas preliminarmente se marcaron identificadores visibles en la franja superior de los píxeles. Pueden incluir nombres, números de expediente y fechas. Las coordenadas sospechosas se guardan en el CSV privado, sin transcribir los identificadores. Las {summary['total_files'] - summary['formally_reviewed_images']} imágenes sin revisión formal permanecen `UNVERIFIED` y `PENDING`. Los valores de metadatos no se copian a este informe.

## Limitaciones del dataset

No hay vínculo confirmado entre archivo, paciente, estudio, lateralidad, posición o diagnóstico. No se infieren fechas clínicas a partir de nombres de archivo. Los indicadores de color y pHash son de cribado y pueden producir falsos positivos.

## Recomendaciones de anonimización

Revisar cada imagen en un entorno local controlado, anotar las regiones identificables con coordenadas y doble revisión. Diseñar máscaras futuras por imagen y validar con un especialista que se preservan anatomía, escalas, velocidades, mediciones, posición y espectros. Conservar originales de acceso restringido y crear copias anonimizadas solo después de la aprobación del protocolo.

## Recomendaciones de etiquetado

Completar `clinical_labels.csv` con fuente clínica verificada; mantener valores desconocidos como `UNKNOWN` o vacíos. Asignar identificadores de paciente y estudio pseudónimos únicamente con registros autorizados. Revisar pares visuales antes de cualquier exclusión. Una futura partición de entrenamiento debe agruparse por paciente.

## Próximos pasos

Revisión visual de privacidad y modalidad de los {summary['total_files']} archivos; reconciliación con estudios clínicos autorizados; confirmación de escalas y mediciones; definición de protocolo de anonimización y etiquetado.
"""
    path.write_text(report, encoding="utf-8")


def run(input_dir: Path, output_dir: Path, metadata_dir: Path | None = None) -> dict:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    metadata_dir = (metadata_dir or input_dir.parent / "metadata").resolve()
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if output_dir == input_dir or input_dir in output_dir.parents:
        raise ValueError("Output must be outside the input directory")
    if metadata_dir == input_dir or input_dir in metadata_dir.parents:
        raise ValueError("Metadata must be outside the input directory")
    LOG.info("Inventariando %s", input_dir)
    rows = inventory(input_dir)
    before = {row["relative_path"]: row["sha256"] for row in rows}
    LOG.info("Leídos %s archivos; calculando duplicados", len(rows))
    pairs = mark_duplicates(rows, input_dir)
    issues = quality_issues(rows)
    LOG.info("Calculando indicadores visuales y gráficas")
    features = visual_features(rows, input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    reviews = update_manual_review(metadata_dir / "manual_visual_review.csv", rows)
    review_status = {review["image_id"]: review["review_status"] for review in reviews}
    for row in rows:
        row["manual_review_status"] = "REVIEWED" if review_status[row["image_id"]] == "REVIEWED" else "PENDING"
    for feature in features:
        if review_status[feature["image_id"]] == "REVIEWED":
            for field in ("text_overlay_review", "panel_count_review", "spectral_review", "calibration_review"):
                feature[field] = "REVIEWED"
    write_csv(metadata_dir / "image_inventory.csv", rows, FIELDS)
    update_labels(metadata_dir / "clinical_labels.csv", rows)
    write_csv(metadata_dir / "visual_review.csv", features,
              ["image_id", "color_pixel_fraction", "top_band_bright_fraction",
               "color_overlay_candidate", "text_overlay_review", "panel_count_review",
               "spectral_review", "calibration_review"])
    write_csv(output_dir / "duplicates_report.csv", pairs,
              ["image_id_a", "image_id_b", "kind", "phash_distance"])
    write_csv(output_dir / "quality_issues.csv", issues,
              ["image_id", "issue_code", "detail"])
    summary = summarize(rows, pairs, issues, features, reviews)
    make_plots(rows, output_dir)
    after = {row["relative_path"]: sha256_file(input_dir / row["relative_path"]) for row in rows}
    if before != after:
        raise RuntimeError("Source image hash changed during processing")
    summary["source_hashes_unchanged"] = True
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(output_dir / "data_quality_report.md", summary, input_dir)
    LOG.info("Verificados SHA-256 originales antes y después: %s archivos", len(rows))
    return summary
