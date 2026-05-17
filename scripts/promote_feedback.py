"""
Promote flagged feedback items into the golden eval dataset.

Fetches all promoted=true feedback from the DB, converts each into a
GoldenQuestion entry, and appends it to eval/golden_questions.jsonl
(skipping duplicates by question_id).

Usage:
    uv run python scripts/promote_feedback.py
    uv run python scripts/promote_feedback.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.core.logging import configure_logging, get_logger
from app.storage.feedback_store import list_feedback

logger = get_logger(__name__)
GOLDEN_PATH = Path("eval/golden_questions.jsonl")


async def promote(dry_run: bool) -> None:
    configure_logging()

    # Load existing golden question IDs to avoid duplicates
    existing_ids: set[str] = set()
    if GOLDEN_PATH.exists():
        for line in GOLDEN_PATH.read_text().splitlines():
            if line.strip():
                q = json.loads(line)
                existing_ids.add(q["id"])

    promoted_items = await list_feedback(promoted=True)
    if not promoted_items:
        print("No promoted feedback items found.")
        return

    new_entries: list[dict] = []
    for item in promoted_items:
        qid = f"fb_{item['feedback_id'][:8]}" if "feedback_id" in item else f"fb_{item['id'][:8]}"
        if qid in existing_ids:
            continue

        # Build a golden question from the feedback
        entry = {
            "id": qid,
            "question": item["question"] or f"[From feedback {item['id'][:8]}]",
            "machine_id": None,
            "expected_evidence_ids": [item["correct_source_id"]] if item.get("correct_source_id") else [],
            "expected_facts": [],
            "expected_refusal": False,
            "_promoted_from": item["id"],
            "_rating": item["rating"],
            "_comment": item["comment"],
        }
        new_entries.append(entry)

    if not new_entries:
        print("No new entries to add (all already in golden dataset).")
        return

    print(f"Found {len(new_entries)} new entries to promote.")
    for e in new_entries:
        print(f"  [{e['id']}] {e['question'][:70]}")

    if dry_run:
        print("\nDry run — nothing written.")
        return

    with GOLDEN_PATH.open("a") as f:
        for entry in new_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\nAppended {len(new_entries)} entries to {GOLDEN_PATH}")
    logger.info("feedback_promoted_to_golden", count=len(new_entries))


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote feedback to golden eval dataset")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    asyncio.run(promote(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
