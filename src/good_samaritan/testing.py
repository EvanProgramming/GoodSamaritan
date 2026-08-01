from __future__ import annotations
import shlex, sys
from pathlib import Path
from .tools import SafeTools
def _python(root:Path)->str:
    isolated=root/'.good-samaritan-venv/bin/python'
    return shlex.quote(str(isolated if isolated.exists() else Path(sys.executable)))
def detect_commands(root:Path)->list[str]:
    python=f"{_python(root)} -m pytest"
    # pytest is the common runner for both declared pytest projects and the
    # ordinary ``test_*.py`` layout.  Do not also invoke unittest discovery:
    # its different collection rules can turn a passing pytest suite into a
    # false failure (or hide a failed pytest run).
    if (root/"pyproject.toml").exists() or (root/"pytest.ini").exists() or any(root.glob("test_*.py")) or (root/"tests").exists():return [python]
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
    results=[]
    for command in commands:
        result=tools.run(command)
        results.append(result.exit_code==0)
    # Every discovered validation command is a gate.  Treating a passing
    # unittest discovery as success after pytest failed let broken patches
    # proceed to review.
    success=bool(results) and all(results)
    return success,commands
