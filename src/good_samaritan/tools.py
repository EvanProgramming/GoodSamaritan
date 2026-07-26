from __future__ import annotations
import os, re, subprocess
from pathlib import Path
from .config import Limits
from .models import CommandResult
class ToolSafetyError(ValueError): pass
class SafeTools:
    def __init__(self,root:Path,limits:Limits):self.root=root.resolve();self.limits=limits;self.commands: list[CommandResult]=[]
    def path(self,path:str)->Path:
        p=(self.root/path).resolve()
        if p!=self.root and self.root not in p.parents:raise ToolSafetyError("path escapes repository")
        if any(x in p.name.lower() for x in (".env","id_rsa","credentials")):raise ToolSafetyError("sensitive file access blocked")
        return p
    def list_files(self,path:str=".")->list[str]:return [str(p.relative_to(self.root)) for p in self.path(path).rglob("*") if p.is_file()][:500]
    def read_file(self,path:str)->str:return self.path(path).read_text(errors="replace")[:30000]
    def write_file(self,path:str,content:str):self.path(path).write_text(content)
    def apply_patch(self,path:str,old:str,new:str):
        target=self.path(path); content=target.read_text()
        if old not in content:raise ToolSafetyError("patch context was not found")
        target.write_text(content.replace(old,new,1))
    def search_text(self,query:str,path:str=".")->list[str]:
        return [f"{p.relative_to(self.root)}:{i}:{line[:300]}" for p in self.path(path).rglob("*") if p.is_file() for i,line in enumerate(p.read_text(errors="ignore").splitlines(),1) if query.lower() in line.lower()][:200]
    def diff(self)->str:return self.run("git diff --no-ext-diff").output
    def run(self,command:str)->CommandResult:
        lowered=command.lower()
        bad=("sudo","rm -rf","curl |","wget |","chmod 777","/etc/","~", " $", "${", "source ")
        if any(x in lowered for x in bad) or re.search(r"(^|\s)(git\s+push|git\s+commit)(\s|$)",lowered):raise ToolSafetyError("dangerous or remote-writing command blocked")
        try:r=subprocess.run(command,shell=True,cwd=self.root,text=True,capture_output=True,timeout=self.limits.command_timeout_seconds,env={"PATH":os.environ.get("PATH","")}) ; out=(r.stdout+r.stderr)[:20000]; result=CommandResult(command=command,exit_code=r.returncode,output=out)
        except subprocess.TimeoutExpired:result=CommandResult(command=command,exit_code=124,output="command timed out")
        self.commands.append(result);return result
    def changed_files(self)->list[str]:return [x for x in self.run("git diff --name-only").output.splitlines() if x]
    def enforce_diff_limits(self):
        files=self.changed_files(); lines=len(self.diff().splitlines())
        if len(files)>self.limits.max_modified_files:raise ToolSafetyError("modified file limit exceeded")
        if lines>self.limits.max_diff_lines:raise ToolSafetyError("diff line limit exceeded")
