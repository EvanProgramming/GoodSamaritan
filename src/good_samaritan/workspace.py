from __future__ import annotations
import shutil, subprocess, tempfile
from pathlib import Path

class WorkspaceError(RuntimeError): pass

class Workspace:
    def __init__(self,base:Path):self.base=base;self.path:Path|None=None
    def clone(self,url:str)->Path:
        self.base.mkdir(parents=True,exist_ok=True);self.path=Path(tempfile.mkdtemp(prefix="attempt-",dir=self.base)); target=self.path/"repo"
        try:
            subprocess.run(["git","clone","--depth","1",url,str(target)],check=True,capture_output=True,text=True,timeout=180)
        except subprocess.TimeoutExpired as error:
            raise WorkspaceError("shallow clone timed out after 180 seconds") from error
        except subprocess.CalledProcessError as error:
            detail=(error.stderr or error.stdout or "git clone returned no diagnostic").strip().replace("\n"," ")[:1000]
            raise WorkspaceError(f"shallow clone failed: {detail}") from error
        return target
    def cleanup(self):
        if self.path and self.path.exists():shutil.rmtree(self.path)
    def __enter__(self):return self
    def __exit__(self,*args):self.cleanup()
