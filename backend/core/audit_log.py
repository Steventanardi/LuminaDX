from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from config import settings

_lock = threading.Lock()
_log_path: Path = settings.logs_dir / "audit.jsonl"


def _write(event: dict[str, Any]) -> None:
    event.setdefault("timestamp", datetime.utcnow().isoformat() + "Z")
    line = json.dumps(event, default=str)
    with _lock:
        with _log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def log_upload(study_id: str, upload_type: str, num_files: int, modality: str | None) -> None:
    _write({
        "event": "upload",
        "study_id": study_id,
        "upload_type": upload_type,
        "num_files": num_files,
        "modality": modality,
    })


def log_analysis_start(job_id: str, study_id: str, model: str) -> None:
    _write({
        "event": "analysis_start",
        "job_id": job_id,
        "study_id": study_id,
        "model": model,
    })


def log_analysis_complete(job_id: str, study_id: str, model: str, duration_s: float, status: str) -> None:
    _write({
        "event": "analysis_complete",
        "job_id": job_id,
        "study_id": study_id,
        "model": model,
        "duration_s": round(duration_s, 2),
        "status": status,
    })


def log_signoff(job_id: str, study_id: str, radiologist_id: str, decision: str) -> None:
    _write({
        "event": "signoff",
        "job_id": job_id,
        "study_id": study_id,
        "radiologist_id": radiologist_id,
        "decision": decision,
    })
