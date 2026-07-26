from __future__ import annotations
import subprocess
from pathlib import Path
from good_samaritan.config import load_settings
from good_samaritan.contribution import pr_body, save_patch
from good_samaritan.discovery import score
from good_samaritan.models import Issue
from good_samaritan.testing import run_validation
from good_samaritan.tools import SafeTools
from good_samaritan.workspace import Workspace

def test_offline_fixture_repo_produces_patch_and_draft(tmp_path):
    origin=tmp_path/'origin';origin.mkdir();subprocess.run(['git','init'],cwd=origin,check=True,capture_output=True)
    (origin/'calc.py').write_text('def add(a, b):\n    return a - b\n')
    (origin/'test_calc.py').write_text('from calc import add\ndef test_add(): assert add(2,3)==5\n')
    subprocess.run(['git','add','.'],cwd=origin,check=True);subprocess.run(['git','-c','user.name=x','-c','user.email=x@y','commit','-m','fixture'],cwd=origin,check=True,capture_output=True)
    s=load_settings();s.runtime.work_directory=tmp_path/'work'
    with Workspace(s.runtime.work_directory) as ws:
        root=ws.clone(str(origin));tools=SafeTools(root,s.limits);tools.write_file('calc.py','def add(a, b):\n    return a + b\n');ok,commands=run_validation(tools);assert ok
        patch=save_patch(root,tmp_path/'result.patch');assert '+    return a + b' in patch.read_text()
        candidate=score(Issue(repository='local/fixture',number=1,title='Fix addition',body='Expected add returns sum'))
        draft=pr_body(candidate,commands);assert 'AI disclosure' in draft and 'Fixes #1' in draft
