"""
Ingestion pipeline entry point.

Usage:
    uv run python -m app.ingestion.run_all
    uv run python -m app.ingestion.run_all --data-dir data/synthetic
"""
from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from app.core.logging import configure_logging, get_logger
from app.ingestion.ingest_documents import ingest_manuals, ingest_operator_notes
from app.ingestion.ingest_tickets import ingest_tickets
from app.ingestion.ingest_timeseries import ingest_anomaly_summaries
from app.storage.database import init_db

logger = get_logger(__name__)


async def run(data_dir: Path) -> None:
    configure_logging()

    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    manifest_path = data_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"No manifest.json in {data_dir}. Run `make seed-data` first."
        )

    logger.info("ingestion_start", data_dir=str(data_dir))
    t0 = time.perf_counter()

    await init_db()

    results: dict[str, int] = {}

    results["manuals"] = await ingest_manuals(data_dir)
    results["tickets"] = await ingest_tickets(data_dir)
    results["anomaly_summaries"] = await ingest_anomaly_summaries(data_dir)
    results["operator_notes"] = await ingest_operator_notes(data_dir)

    elapsed = round(time.perf_counter() - t0, 1)
    total = sum(results.values())

    logger.info("ingestion_complete", total_chunks=total, elapsed_s=elapsed, **results)

    print(f"\nIngestion complete in {elapsed}s")
    for key, count in results.items():
        print(f"  {key:<20} {count:>5} chunks")
    print(f"  {'TOTAL':<20} {total:>5} chunks")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full ingestion pipeline")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/synthetic"),
        help="Directory containing generated data files",
    )
    args = parser.parse_args()
    asyncio.run(run(args.data_dir))


if __name__ == "__main__":
    main()
