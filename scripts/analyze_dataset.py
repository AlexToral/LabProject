"""Run local data quality analysis without modifying source images."""
import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data.pipeline import run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "MLo" / "dataset" / "raw")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "data_quality")
    parser.add_argument("--metadata", type=Path, help="Default: sibling metadata folder beside raw")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        summary = run(args.input, args.output, args.metadata)
    except (OSError, ValueError, RuntimeError) as exc:
        logging.error("Pipeline failed: %s", exc)
        return 1
    print(f"Completed: {summary['valid_images']} valid, {summary['invalid_images']} invalid; "
          f"{summary['exact_duplicate_pairs']} exact pairs, "
          f"{summary['visual_candidate_pairs']} visual candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
