from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from .database import Database
def generate(db:Database,site:Path)->tuple[Path,Path]:
    site.mkdir(parents=True,exist_ok=True);(site/'reports').mkdir(exist_ok=True);(site/'contributions').mkdir(exist_ok=True);(site/'lessons').mkdir(exist_ok=True)
    stats=db.statistics();contrib=[dict(x) for x in db.conn.execute("SELECT * FROM contributions ORDER BY updated_at DESC").fetchall()];lessons=[dict(x) for x in db.lessons()]
    (site/'stats.json').write_text(json.dumps({**stats,"contributions":contrib,"lessons":lessons},indent=2))
    day=date.today().isoformat();report=site/'reports'/f'{day}.md';report.write_text(f"# Daily Good Deeds — {day}\n\n## Statistics\n"+"\n".join(f"- {k.replace('_',' ').title()}: {v}" for k,v in stats.items())+"\n\n## Recent contributions\n"+"\n".join(f"- {x['repository']}#{x['issue_number']}: {x['status']}" for x in contrib[:10]))
    for item in contrib:
        (site/'contributions'/f"{item['id']}.md").write_text(f"# Contribution #{item['id']}\n\nRepository: {item['repository']}\n\nIssue: #{item['issue_number']}\n\nWhat I did: {item['summary']}\n\nStatus: {item['status']}\n\nPR: {item['pr_url'] or 'Not created'}\n")
    return site/'stats.json',report
