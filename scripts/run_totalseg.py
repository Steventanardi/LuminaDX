"""
Runs TotalSegmentator in an isolated process with a proper __main__ guard.
Called as a subprocess from core/segmentation.py so that nnU-Net's spawned
DataLoader workers can safely re-import __main__ without restarting uvicorn.

Usage:
    python run_totalseg.py <json_args>

JSON args keys:
    input   : str  — path to input NIfTI file
    output  : str  — path to output directory
    task    : str  — TotalSegmentator task (default "total")
    roi_subset : list[str] | null
    device  : str  — "gpu" | "cpu"
    fast    : bool
"""
import os
import sys
import json

# Must be set before any nnunetv2 import
os.environ["nnUNet_n_proc_DA"] = "2"
os.environ["nnUNet_def_n_proc"] = "2"

if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    from pathlib import Path
    from totalsegmentator.python_api import totalsegmentator

    kwargs = dict(
        input=Path(args["input"]),
        output=Path(args["output"]),
        device=args.get("device", "gpu"),
        quiet=True,
        nr_thr_resamp=1,
        nr_thr_saving=1,
    )
    task = args.get("task", "total")
    if task != "total":
        kwargs["task"] = task
    if args.get("roi_subset"):
        kwargs["roi_subset"] = args["roi_subset"]
    if args.get("fast"):
        kwargs["fast"] = True

    totalsegmentator(**kwargs)
