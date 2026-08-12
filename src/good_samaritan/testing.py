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
    root=tools.root
    # Do not bootstrap a Python environment for a JavaScript/Zig repository.
    # That unnecessary pip step was the source of long apparent validation
    # hangs before the actual npm gate even started.
    if (root/'package.json').exists():
        commands=["npm ci --ignore-scripts"] if (root/'package-lock.json').exists() else []
        for command in commands:
            if tools.run(command).exit_code!=0:break
        return commands
    commands=[f"{shlex.quote(sys.executable)} -m venv .good-samaritan-venv",f"{shlex.quote(str(root/'.good-samaritan-venv/bin/python'))} -m pip install pytest"]
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
    observed=[]
    for command in commands:
        result=tools.run(command)
        observed.append(result)
        results.append(result.exit_code==0)
    # A clone can be valid while the daemon image lacks npm. Do not spend
    # repair/model calls asking the agent to fix an environment failure. Keep
    # real test failures strict; this fallback applies only when npm itself is
    # unavailable and still requires a clean diff.
    if commands and any(command.startswith("npm ") for command in commands) and any(
        result.exit_code==127 and "not found" in getattr(result,"output","").lower()
        for result in observed
    ):
        results=[result.exit_code==0 for command,result in zip(commands,observed)
                 if not (command.startswith("npm ") and result.exit_code==127)]
        commands.append("git diff --check")
        results.append(tools.run("git diff --check").exit_code==0)
    # Every discovered validation command is a gate.  Treating a passing
    # unittest discovery as success after pytest failed let broken patches
    # proceed to review.
    success=bool(results) and all(results)
    return success,commands
