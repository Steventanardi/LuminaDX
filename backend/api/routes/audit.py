from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from config import settings

router = APIRouter()

_LOG_PATH = settings.logs_dir / "audit.jsonl"


@router.get("/")
async def get_audit_log(
    n: int = Query(default=100, ge=1, le=1000, description="Number of most-recent entries to return"),
    event: Optional[str] = Query(default=None, description="Filter by event type"),
) -> Dict[str, Any]:
    if not _LOG_PATH.exists():
        return {"entries": [], "total": 0}

    lines = _LOG_PATH.read_text(encoding="utf-8").splitlines()
    entries: List[Dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if event is None or obj.get("event") == event:
                entries.append(obj)
        except json.JSONDecodeError:
            pass

    total = len(entries)
    return {"entries": entries[-n:], "total": total}
