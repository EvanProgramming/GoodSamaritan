from __future__ import annotations
import shlex, sys
from pathlib import Path
from .tools import SafeTools
def _python(root:Path)->str:
    isolated=root/'.good-samaritan-venv/bin/python'
    return shlex.quote(str(isolated if isolated.exists() else Path(sys.executable)))
def detect_commands(root:Path)->list[str]:
    python=f"{_python(root)} -m pytest"
    if (root/"pyproject.toml").exists() or (root/"pytest.ini").exists() or any(root.glob("test_*.py")) or (root/"tests").exists():return [python,f"{_python(root)} -m unittest discover"]
    if (root/"package.json").exists():return ["npm test", "npm run lint"]
    if (root/"Cargo.toml").exists():return ["cargo test"]
    if (root/"go.mod").exists():return ["go test ./..."]
    if (root/"Makefile").exists():return ["make test"]
    # A repository without a test framework can still receive a syntax and
    # whitespace check. The model review remains a separate gate.
    return ["git diff --check"]
def install_dependencies(tools:SafeTools)->list[str]:
    """Install declared dependencies only inside the disposable repository clone."""
    root=tools.root; commands=[f"{shlex.quote(sys.executable)} -m venv .good-samaritan-venv",f"{shlex.quote(str(root/'.good-samaritan-venv/bin/python'))} -m pip install pytest"]
    requirements=next((p for p in (root/'requirements.txt',root/'requirements-dev.txt') if p.exists()),None)
    if requirements:commands.append(f"{shlex.quote(str(root/'.good-samaritan-venv/bin/python'))} -m pip install -r {shlex.quote(requirements.name)}")
    elif (root/'pyproject.toml').exists() or (root/'setup.py').exists():commands.append(f"{shlex.quote(str(root/'.good-samaritan-venv/bin/python'))} -m pip install .")
    elif (root/'package-lock.json').exists():commands.append("npm ci --ignore-scripts")
    for command in commands:
        if tools.run(command).exit_code!=0:break
    return commands
def run_validation(tools:SafeTools,allow_dependency_install:bool=False)->tuple[bool,list[str]]:
    if allow_dependency_install and detect_commands(tools.root):install_dependencies(tools)
    commands=detect_commands(tools.root); success=False
    for command in commands:
        result=tools.run(command)
        success=success or result.exit_code==0
    return success,commands
