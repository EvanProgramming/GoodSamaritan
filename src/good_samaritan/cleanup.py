"""Cleanup only Good Samaritan-owned, reproducible runtime artifacts."""
from __future__ import annotations
import shutil
from pathlib import Path

def cleanup_orphan_workspaces(work_directory:Path)->list[Path]:
    """Remove only stale `attempt-*` directories under the configured work root."""
    root=work_directory.resolve()
    if not root.exists():return []
    removed=[]
    for path in root.iterdir():
        if path.is_dir() and path.name.startswith("attempt-"):
            shutil.rmtree(path);removed.append(path)
    return removed

def cleanup_attempt_artifacts(work_directory:Path,attempt_id:int)->list[Path]:
    """Delete patch/PR drafts once a remote PR reaches a terminal state."""
    root=work_directory.resolve();removed=[]
    for suffix in (".patch","-pr.md"):
        path=(root/f"attempt-{attempt_id}{suffix}").resolve()
        if root in path.parents and path.is_file():path.unlink();removed.append(path)
    return removed
