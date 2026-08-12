from __future__ import annotations
import os, re, subprocess
from pathlib import Path
from .config import Limits
from .models import CommandResult
class ToolSafetyError(ValueError): pass
class SafeTools:
    _blocked_parts={".git",".good-samaritan-home",".good-samaritan-venv"}
    def __init__(self,root:Path,limits:Limits):
        self.root=root.resolve();self.limits=limits;self.commands: list[CommandResult]=[]
        # Validation runs create an isolated HOME and, optionally, a virtual
        # environment inside this disposable clone.  Keep those runtime files
        # out of `git add -A` while allowing a genuine new source/test file to
        # remain visible to the normal diff and review gates.
        exclude=self.root/'.git'/'info'/'exclude'
        if exclude.exists():
            existing=exclude.read_text(errors="replace")
            additions="".join(pattern+"\n" for pattern in (".good-samaritan-home/",".good-samaritan-venv/") if pattern not in existing)
            if additions:exclude.write_text(existing+additions)
    def path(self,path:str)->Path:
        p=(self.root/path).resolve()
        if p!=self.root and self.root not in p.parents:raise ToolSafetyError("path escapes repository")
        if p!=self.root and any(part in self._blocked_parts for part in p.relative_to(self.root).parts):raise ToolSafetyError("internal runtime path is blocked")
        if any(x in p.name.lower() for x in (".env","id_rsa","credentials")):raise ToolSafetyError("sensitive file access blocked")
        return p
    def _files(self,path:str="."):
        base=self.path(path)
        return [p for p in base.rglob("*") if p.is_file() and not any(part in self._blocked_parts for part in p.relative_to(self.root).parts)]
    def list_files(self,path:str=".")->list[str]:return [str(p.relative_to(self.root)) for p in self._files(path)][:500]
    def read_file(self,path:str)->str:
        target=self.path(path)
        if not target.is_file():raise ToolSafetyError("file does not exist or is not a regular file")
        return target.read_text(errors="replace")[:30000]
    def write_file(self,path:str,content:str):
        target=self.path(path)
        if target.exists() and not target.is_file():raise ToolSafetyError("target is not a regular file")
        existed=target.exists();target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content)
        # Make a legitimate new file visible to git diff without staging its
        # contents.  The later submission still performs the actual add.
        if not existed and (self.root/'.git').exists():
            subprocess.run(["git","add","-N","--",str(target.relative_to(self.root))],cwd=self.root,check=True,capture_output=True,text=True)
    def apply_patch(self,path:str,old:str,new:str):
        target=self.path(path)
        if not target.is_file():raise ToolSafetyError("target is not a regular file")
        content=target.read_text()
        if old not in content:raise ToolSafetyError("patch context was not found")
        target.write_text(content.replace(old,new,1))
    def apply_patch_document(self,document:str):
        """Apply the common ``*** Begin Patch`` format emitted by coding models."""
        text=document.strip()
        if text.startswith("```"):
            text=text.removeprefix("```").removesuffix("```").strip()
        if text.startswith("--- ") and "+++ " in text:
            # Accept standard git unified diffs returned by coding models.
            normalized=["*** Begin Patch\n"]
            for line in text.splitlines(keepends=True):
                if line.startswith("--- "):continue
                if line.startswith("+++ "):
                    path=line[4:].strip().removeprefix("b/")
                    normalized.append(f"*** Update File: {path}\n")
                else:normalized.append(line)
            normalized.append("*** End Patch\n");text="".join(normalized)
        text=text.rstrip()
        if text.startswith("*** Begin Patch"):
            text=text[len("*** Begin Patch"):].lstrip("\r\n")
        if text.endswith("*** End Patch"):
            text=text[:-len("*** End Patch")].strip("\r\n")+"\n"
        lines=text.splitlines(keepends=True)
        current:dict|None=None; hunk:list[str]=[]; records:list[tuple[str,str,list[str]]]=[]
        def flush_hunk():
            nonlocal hunk
            if current is not None and hunk:current["hunks"].append(hunk)
            hunk=[]
        def flush_file():
            nonlocal current
            flush_hunk()
            if current is not None:records.append((current["kind"],current["path"],current["hunks"]))
            current=None
        for line in lines:
            header=re.match(r"^\*\*\* (Update|Add|Delete) File: (.+?)\s*$",line.rstrip("\r\n"))
            if header:
                flush_file();current={"kind":header.group(1),"path":header.group(2),"hunks":[]};continue
            if line.startswith("@@"):
                flush_hunk();continue
            if line.startswith("\\ No newline"):
                continue
            if current is None:raise ToolSafetyError("patch document is missing a file header")
            if line[0] not in " +-":raise ToolSafetyError("unsupported patch document line")
            hunk.append(line)
        flush_file()
        if not records:raise ToolSafetyError("patch document contained no file changes")
        for kind,path,hunks in records:
            if kind=="Delete":raise ToolSafetyError("file deletion is not supported by the bounded patch tool")
            if kind=="Add":
                content="".join(line[1:] for h in hunks for line in h if line.startswith("+"))
                self.write_file(path,content);continue
            for h in hunks:
                old="".join(line[1:] for line in h if line.startswith((" ","-")))
                new="".join(line[1:] for line in h if line.startswith((" ","+")))
                if not old:raise ToolSafetyError("update patch has no context")
                self.apply_patch(path,old,new)
    def search_text(self,query:str,path:str=".")->list[str]:
        return [f"{p.relative_to(self.root)}:{i}:{line[:300]}" for p in self._files(path) for i,line in enumerate(p.read_text(errors="ignore").splitlines(),1) if query.lower() in line.lower()][:200]
    def diff(self)->str:return self.run("git diff --no-ext-diff").output
    def run(self,command:str)->CommandResult:
        lowered=command.lower()
        bad=("sudo","rm -rf","curl |","wget |","chmod 777","/etc/","~", " $", "${", "source ")
        if any(x in lowered for x in bad) or re.search(r"(^|\s)(git\s+push|git\s+commit)(\s|$)",lowered):raise ToolSafetyError("dangerous or remote-writing command blocked")
        # The subprocess already starts in the repository.  An absolute or
        # parent-directory `cd` defeats that invariant and was the cause of an
        # agent repeatedly searching / instead of the cloned project.
        if re.search(r"(^|[;&|]\s*)cd\s+(?:/|~|\.\.)",command):
            raise ToolSafetyError("command changes directory outside repository")
        # Commands run with a disposable HOME inside the cloned repository so
        # package managers can work without seeing the operator's credentials,
        # shell profiles, or ordinary cache directories.
        isolated_home=self.root/'.good-samaritan-home'; isolated_home.mkdir(exist_ok=True)
        path_entries=[os.environ.get("PATH","")]
        # launchd intentionally supplies a minimal PATH.  Add the verified
        # user-local Node runtime so npm/package-manager validation works in
        # the daemon just as it does in an interactive shell.
        node_bin=Path.home()/".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin"
        if node_bin.is_dir():path_entries.insert(0,str(node_bin))
        env={"PATH":os.pathsep.join(x for x in path_entries if x),"HOME":str(isolated_home),"PIP_CACHE_DIR":str(isolated_home/'pip-cache'),"PIP_DISABLE_PIP_VERSION_CHECK":"1","GIT_TERMINAL_PROMPT":"0","CI":"true"}
        try:r=subprocess.run(command,shell=True,cwd=self.root,text=True,capture_output=True,timeout=self.limits.command_timeout_seconds,env=env) ; out=(r.stdout+r.stderr)[:20000]; result=CommandResult(command=command,exit_code=r.returncode,output=out)
        except subprocess.TimeoutExpired:result=CommandResult(command=command,exit_code=124,output="command timed out")
        self.commands.append(result);return result
    def changed_files(self)->list[str]:return [x for x in self.run("git diff --name-only").output.splitlines() if x]
    def enforce_diff_limits(self):
        files=self.changed_files(); lines=len(self.diff().splitlines())
        if len(files)>self.limits.max_modified_files:raise ToolSafetyError("modified file limit exceeded")
        if lines>self.limits.max_diff_lines:raise ToolSafetyError("diff line limit exceeded")
