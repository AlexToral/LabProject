"""Data quality flags are review prompts, never deletion rules."""
from collections import Counter

EXPECTED_RESOLUTIONS = {(808, 842), (1626, 842)}
FORMAT_BY_EXTENSION = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG",
                       ".tif": "TIFF", ".tiff": "TIFF", ".bmp": "BMP", ".webp": "WEBP"}
REQUIRED_VALID = ("actual_format", "width_px", "height_px", "channels", "color_mode",
                  "sha256", "aspect_ratio", "intensity_mean", "intensity_std")


def quality_issues(rows: list[dict], expected_resolutions=EXPECTED_RESOLUTIONS) -> list[dict]:
    issues = []

    def flag(row, code, detail=""):
        issues.append({"image_id": row["image_id"], "issue_code": code, "detail": detail})

    for row in rows:
        if row["integrity_status"] != "VALID":
            flag(row, row["integrity_status"])
            continue
        expected_format = FORMAT_BY_EXTENSION.get(row["extension"])
        if expected_format != row["actual_format"]:
            flag(row, "EXTENSION_MISMATCH", f"{row['extension']} vs {row['actual_format']}")
        if expected_resolutions and (row["width_px"], row["height_px"]) not in expected_resolutions:
            flag(row, "UNEXPECTED_RESOLUTION", f"{row['width_px']}x{row['height_px']}")
        if row["intensity_mean"] <= 1:
            flag(row, "NEAR_BLACK")
        elif row["intensity_mean"] >= 254:
            flag(row, "NEAR_WHITE")
        if row["intensity_std"] < 5:
            flag(row, "LOW_CONTRAST")
        if row["exact_duplicate"]:
            flag(row, "EXACT_DUPLICATE")
        if row["possible_visual_duplicate"]:
            flag(row, "VISUAL_DUPLICATE_CANDIDATE")
        for field in REQUIRED_VALID:
            if row[field] == "" or row[field] is None:
                flag(row, "MISSING_FIELD", field)
    return issues


def issue_counts(issues: list[dict]) -> dict:
    return dict(sorted(Counter(issue["issue_code"] for issue in issues).items()))
