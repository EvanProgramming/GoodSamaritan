from __future__ import annotations
import shlex, sys
from pathlib import Path
from .tools import SafeTools
def detect_commands(root:Path)->list[str]:
    python=f"{shlex.quote(sys.executable)} -m pytest"
    if (root/"pyproject.toml").exists() or (root/"pytest.ini").exists():return [python]
    if any(root.glob("test_*.py")) or (root/"tests").exists():return [python]
    if (root/"package.json").exists():return ["npm test", "npm run lint"]
    if (root/"Cargo.toml").exists():return ["cargo test"]
    if (root/"go.mod").exists():return ["go test ./..."]
    if (root/"Makefile").exists():return ["make test"]
    return []
def run_validation(tools:SafeTools)->tuple[bool,list[str]]:
    commands=detect_commands(tools.root); success=False
    for command in commands:
        result=tools.run(command)
        success=success or result.exit_code==0
    return success,commands
