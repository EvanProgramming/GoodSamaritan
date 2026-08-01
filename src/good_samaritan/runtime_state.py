"""Small, local-only status hand-off from the daemon to the dashboard."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

def _path(database:Path)->Path:
    return database.parent/"daemon-status.json"

def _manual_path(database:Path)->Path:
    return database.parent/"manual-run.request"

def request_manual_run(database:Path)->None:
    """Queue one immediate autonomous discovery cycle for the daemon."""
    _manual_path(database).write_text(datetime.now(timezone.utc).isoformat())

def consume_manual_run(database:Path)->bool:
    """Consume a queued dashboard request without interrupting active work."""
    target=_manual_path(database)
    if not target.exists():return False
    try:target.unlink()
    except FileNotFoundError:return False
    return True

def write(database:Path,state:str,detail:str="",wait_seconds:int|None=None)->None:
    payload={"state":state,"detail":detail,"updated_at":datetime.now(timezone.utc).isoformat()}
    if wait_seconds is not None:payload["wait_seconds"]=wait_seconds
    path=_path(database);temporary=path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload));temporary.replace(path)

def read(database:Path)->dict[str,object]:
    try:return json.loads(_path(database).read_text())
    except (OSError,json.JSONDecodeError):return {"state":"UNKNOWN","detail":"No daemon status has been recorded yet."}
