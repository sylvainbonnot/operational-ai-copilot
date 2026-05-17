from __future__ import annotations

import json
from pathlib import Path

from app.models.evaluation import GoldenQuestion


def load_golden_questions(path: Path) -> list[GoldenQuestion]:
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    return [GoldenQuestion(**json.loads(line)) for line in lines]
