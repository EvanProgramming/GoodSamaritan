from __future__ import annotations
import shutil, subprocess, tempfile, time
from pathlib import Path

class WorkspaceError(RuntimeError): pass

class Workspace:
    def __init__(self,base:Path):self.base=base;self.path:Path|None=None
    def clone(self,url:str,timeout:int=180)->Path:
        self.base.mkdir(parents=True,exist_ok=True);self.path=Path(tempfile.mkdtemp(prefix="attempt-",dir=self.base)); target=self.path/"repo"
        transient_markers=("early eof","unexpected disconnect","http2","curl ","connection reset","connection refused","timed out")
        for attempt in range(3):
            try:
                subprocess.run(["git","clone","--depth","1",url,str(target)],check=True,capture_output=True,text=True,timeout=timeout)
                return target
            except subprocess.TimeoutExpired as error:
                if attempt<2:
                    shutil.rmtree(target,ignore_errors=True);time.sleep(2**attempt);continue
                raise WorkspaceError(f"shallow clone timed out after {timeout} seconds") from error
            except subprocess.CalledProcessError as error:
                detail=(error.stderr or error.stdout or "git clone returned no diagnostic").strip().replace("\n"," ")[:1000]
                if attempt<2 and any(marker in detail.lower() for marker in transient_markers):
                    shutil.rmtree(target,ignore_errors=True);time.sleep(2**attempt);continue
                raise WorkspaceError(f"shallow clone failed: {detail}") from error
        raise WorkspaceError("shallow clone failed after transient retries")
    def cleanup(self):
        if self.path and self.path.exists():shutil.rmtree(self.path)
    def __enter__(self):return self
    def __exit__(self,*args):self.cleanup()
