from __future__ import annotations
from pathlib import Path
from .models import Candidate
AI_DISCLOSURE="This contribution was autonomously prepared by Good Samaritan, an experimental AI open-source contributor. AI was used for analysis and code modification. The code and test results should be reviewed normally by the project maintainers."
def pr_body(candidate:Candidate,tests:list[str],limitations:str="") -> str:
    test_lines='\n'.join(f"- `{x}`" for x in tests) or "- No validation command was available."
    return f"Fixes #{candidate.issue.number}\n\n## Summary\nAddresses: {candidate.issue.title}\n\n## Changes\nA focused change was prepared for this issue.\n\n## Tests\n{test_lines}\n\n## Known limitations\n{limitations or 'Please review against project-specific expectations.'}\n\n## AI disclosure\n{AI_DISCLOSURE}\n"
def save_patch(root:Path,out:Path)->Path:
    import subprocess
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(subprocess.run(["git","diff","--no-ext-diff"],cwd=root,text=True,capture_output=True,check=True).stdout);return out
