"""Debug: show what source_ids are actually returned for golden questions."""
import asyncio
from app.storage.vector_store import similarity_search

QUERIES = [
    ("Q1  bearing interval",    "What is the bearing inspection interval for compressors?",           None,             5),
    ("Q6  ISO 10816 zones",     "What are the vibration severity zones per ISO 10816?",               None,             8),
    ("Q8  LOTO procedure",      "What is the lockout tagout LOTO safety procedure before maintenance?", None,           8),
    ("Q14 bearing freq faults", "What frequency signatures indicate a bearing defect in vibration spectra?", None,      8),
    ("Q17 compressor_17 heat",  "Why does compressor_17 overheat and what should be checked first?",  "compressor_17",  8),
]

async def main() -> None:
    for label, query, machine_id, top_k in QUERIES:
        filters = {"machine_id": machine_id} if machine_id else None
        chunks = await similarity_search(query, top_k=top_k, filters=filters)
        print(f"\n=== {label} ===")
        if not chunks:
            print("  (no results)")
        for c in chunks:
            print(f"  source_id={c.source_id!r:45s}  type={c.source_type!r:15s}  score={c.score}")

if __name__ == "__main__":
    asyncio.run(main())
