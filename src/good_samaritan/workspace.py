from __future__ import annotations
import shutil, subprocess, tempfile
from pathlib import Path
class Workspace:
    def __init__(self,base:Path):self.base=base;self.path:Path|None=None
    def clone(self,url:str)->Path:
        self.base.mkdir(parents=True,exist_ok=True);self.path=Path(tempfile.mkdtemp(prefix="attempt-",dir=self.base)); target=self.path/"repo"; subprocess.run(["git","clone","--depth","1",url,str(target)],check=True,capture_output=True,text=True,timeout=180);return target
    def cleanup(self):
        if self.path and self.path.exists():shutil.rmtree(self.path)
    def __enter__(self):return self
    def __exit__(self,*args):self.cleanup()
