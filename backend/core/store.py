"""Lightweight on-disk persistence for analysis jobs and slice blobs.

Jobs were previously held only in module-level dicts, so a backend restart lost
every report and sign-off, and slice PNGs accumulated in RAM unbounded. This
module persists jobs as JSON (one file per job) and offloads slice blobs to disk
so they never sit in memory. It is deliberately dependency-free (no DB) to keep
the research prototype simple while surviving restarts and bounding memory.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from loguru import logger

from config import settings
from models.schemas import AnalysisJob, AnalysisStatus

_TERMINAL = {AnalysisStatus.COMPLETE, AnalysisStatus.FAILED}

_JOBS_DIR = settings.processed_dir / "jobs"
_SLICES_DIR = settings.processed_dir / "slices"
_JOBS_DIR.mkdir(parents=True, exist_ok=True)
_SLICES_DIR.mkdir(parents=True, exist_ok=True)


def save_job(job: AnalysisJob) -> None:
    """Persist a job snapshot (atomic write via temp file + replace)."""
    try:
        tmp = _JOBS_DIR / f"{job.job_id}.json.tmp"
        tmp.write_text(job.model_dump_json(), encoding="utf-8")
        tmp.replace(_JOBS_DIR / f"{job.job_id}.json")
    except Exception as exc:
        logger.warning(f"Could not persist job {job.job_id[:8]}: {exc}")


def load_all_jobs() -> Dict[str, AnalysisJob]:
    """Load every persisted job at startup so history survives restarts.

    Any job that was still running when the process stopped can never resume (no
    background task exists for it), so it is healed to FAILED here — otherwise the
    UI and /history would wait on it forever.
    """
    jobs: Dict[str, AnalysisJob] = {}
    healed = 0
    for p in _JOBS_DIR.glob("*.json"):
        try:
            job = AnalysisJob.model_validate_json(p.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"Skip corrupt job file {p.name}: {exc}")
            continue
        if job.status not in _TERMINAL:
            job.status = AnalysisStatus.FAILED
            job.error = "Interrupted by backend restart"
            job.current_step = "Failed"
            save_job(job)
            healed += 1
        jobs[p.stem] = job
    if jobs:
        logger.info(f"Loaded {len(jobs)} persisted job(s) from disk ({healed} healed from interruption)")
    return jobs


def save_slices(job_id: str, slices: List[str], raw: List[str]) -> None:
    """Write slice blobs to disk instead of keeping them in RAM."""
    try:
        tmp = _SLICES_DIR / f"{job_id}.json.tmp"
        tmp.write_text(json.dumps({"slices": slices, "raw": raw}), encoding="utf-8")
        tmp.replace(_SLICES_DIR / f"{job_id}.json")
    except Exception as exc:
        logger.warning(f"Could not persist slices for {job_id[:8]}: {exc}")


def load_slices(job_id: str) -> Tuple[List[str], List[str]]:
    p = _SLICES_DIR / f"{job_id}.json"
    if not p.exists():
        return [], []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("slices", []), data.get("raw", [])
    except Exception:
        return [], []
