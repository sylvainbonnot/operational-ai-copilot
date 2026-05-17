"""Quick demo: fires a question at the running copilot API and pretty-prints the response."""
import asyncio
import json
import sys

import httpx

BASE_URL = "http://localhost:8000"

DEMO_QUESTIONS = [
    {"question": "Why did compressor_17 fail twice this month?", "machine_id": "compressor_17"},
    {"question": "Summarize recent anomalies on Line 3.", "machine_id": None},
    {"question": "What should an operator check first for abnormal vibration?", "machine_id": None},
]


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        health = await client.get("/health")
        print(f"API status: {health.json()['status']}\n")

        for q in DEMO_QUESTIONS:
            print(f"Q: {q['question']}")
            resp = await client.post("/ask", json=q)
            if resp.status_code == 501:
                print("  (not implemented yet — Phase 5)\n")
            else:
                data = resp.json()
                print(f"  A: {data.get('answer', '—')}")
                print(f"  Grounded: {data.get('grounded')}  Confidence: {data.get('confidence')}\n")


if __name__ == "__main__":
    asyncio.run(main())
