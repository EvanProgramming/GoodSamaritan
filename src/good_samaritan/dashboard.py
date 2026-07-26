"""A dependency-free, localhost-only operational dashboard."""
from __future__ import annotations
import html, json, os, re, sqlite3, subprocess, sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ACTIVE={"SELECTED","CLONING","ANALYZING","EDITING","TESTING","REVIEWING"}

def _rows(db: Path, sql: str, params: tuple=()) -> list[dict]:
    if not db.exists(): return []
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        return [dict(row) for row in conn.execute(sql,params).fetchall()]

def snapshot(db: Path) -> dict:
    attempts=_rows(db,"SELECT * FROM attempts ORDER BY updated_at DESC, id DESC")
    current=next((a for a in attempts if a["status"] in ACTIVE),None)
    commands=_rows(db,"SELECT c.*,a.repository,a.issue_number FROM commands c JOIN attempts a ON a.id=c.attempt_id ORDER BY c.id DESC LIMIT 30")
    pr_states=_rows(db,"SELECT p.*,a.repository,a.issue_number,a.pr_url FROM pr_status p JOIN attempts a ON a.id=p.attempt_id ORDER BY p.updated_at DESC")
    interactions=_rows(db,"SELECT i.*,a.repository,a.issue_number FROM interactions i JOIN attempts a ON a.id=i.attempt_id ORDER BY i.created_at DESC LIMIT 50")
    events=_rows(db,"SELECT e.*,a.repository,a.issue_number FROM attempt_events e JOIN attempts a ON a.id=e.attempt_id ORDER BY e.id DESC LIMIT 30")
    providers={}
    for item in attempts:
        if item.get("provider"): providers[item["provider"]]=providers.get(item["provider"],0)+1
    log_path=db.parent/'targeted-run.log';target_log=log_path.read_text(errors='replace')[-6000:] if log_path.exists() else ''
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"current":current,"attempts":attempts[:100],"commands":commands,"pr_states":pr_states,"interactions":interactions,"events":events,"target_log":target_log,"summary":{"attempts":len(attempts),"ready":sum(a["status"]=="READY" for a in attempts),"prs":sum(bool(a["pr_url"]) for a in attempts),"failed":sum(a["status"]=="FAILED" for a in attempts),"providers":providers}}

PAGE="""<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>Good Samaritan · Operations</title><style>
body{font:15px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:#101318;color:#e8edf2;margin:0}main{max-width:1200px;margin:auto;padding:28px}h1{margin:0 0 4px}.muted{color:#a9b4c1}.cards{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0}.card{background:#1b222c;padding:14px 18px;border-radius:9px;min-width:120px}.value{font-size:25px;font-weight:700}section{background:#161d26;border:1px solid #293544;border-radius:10px;padding:18px;margin:16px 0}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid #293544;vertical-align:top}th{color:#a9b4c1}a{color:#86c8ff}.status{font-weight:700}.active{color:#ffd166}.ready{color:#8ce99a}.failed{color:#ff8787}pre{white-space:pre-wrap;margin:0;max-width:600px;overflow:auto}.empty{padding:15px;background:#1b222c;border-radius:7px}</style>
<main><h1>Good Samaritan</h1><div class=muted>Local operations dashboard · refreshes every 10 seconds</div><section><h2>Controls</h2><button onclick="service('start')">Start daemon</button> <button onclick="service('stop')">Stop daemon</button><div><input id=repo placeholder="owner/repository" aria-label="Target repository"><button type=button onclick="startTarget()">Find Issue and contribute</button></div><div id=notice class=muted></div></section><section id=targetprogress><h2>Targeted run progress</h2><div class=empty>No targeted run yet.</div></section><section id=agentprogress><h2>Current agent activity</h2><div class=empty>No agent actions yet.</div></section><div id=app>Loading…</div></main>
<script>const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function status(s){let c=['SELECTED','CLONING','ANALYZING','EDITING','TESTING','REVIEWING'].includes(s)?'active':s==='READY'||s==='PR_CREATED'?'ready':s==='FAILED'?'failed':'';return `<span class="status ${c}">${esc(s)}</span>`}
async function post(url,data=''){let n=document.querySelector('#notice');try{let r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:data});let x=await r.json();n.textContent=x.message||'Request completed.'}catch(e){n.textContent='Request failed: '+e}}function service(x){post('/api/service/'+x)}function startTarget(){let r=document.querySelector('#repo').value.trim();if(!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(r)){document.querySelector('#notice').textContent='Enter exactly owner/repository, without a GitHub URL.';return}if(confirm('Start a real contribution attempt for '+r+'?'))post('/api/run-repository','repository='+encodeURIComponent(r))}
function render(d){let s=d.summary,c=d.current;document.querySelector('#app').innerHTML=`<div class=cards><div class=card><div class=value>${s.attempts}</div>Attempts</div><div class=card><div class=value>${s.ready}</div>Ready patches</div><div class=card><div class=value>${s.prs}</div>PRs created</div><div class=card><div class=value>${s.failed}</div>Failures</div><div class=card><div class=value>${esc(Object.entries(s.providers).map(x=>x.join(': ')).join(', ')||'—')}</div>Models used</div></div><section><h2>Current activity</h2>${c?`<table><tr><th>Repository / Issue</th><th>Stage</th><th>Model</th><th>Updated</th></tr><tr><td>${esc(c.repository)} <a href="https://github.com/${esc(c.repository)}/issues/${c.issue_number}" target=_blank>#${c.issue_number}</a><br>${esc(c.reasons)}</td><td>${status(c.status)}</td><td>${esc(c.provider||'—')} / ${esc(c.model||'—')}</td><td>${esc(c.updated_at)}</td></tr></table>`:'<div class=empty>Idle — waiting for the next scheduled run.</div>'}</section><section><h2>Pull-request health</h2><table><tr><th>PR</th><th>Merge</th><th>Review</th><th>Checks</th><th>Details</th></tr>${d.pr_states.map(x=>`<tr><td><a href="${esc(x.pr_url)}" target=_blank>${esc(x.repository)}#${x.issue_number}</a></td><td>${esc(x.mergeable_state)}</td><td>${status(x.review_state)}</td><td>${status(x.checks_state)}</td><td>${esc(x.details)}</td></tr>`).join('')||'<tr><td colspan=5>No created PRs to monitor.</td></tr>'}</table></section><section><h2>Maintainer conversations</h2><table><tr><th>Issue / PR</th><th>Author</th><th>Incoming feedback</th><th>Response status</th></tr>${d.interactions.map(x=>`<tr><td>${esc(x.repository)}#${x.issue_number}</td><td>${esc(x.author)}</td><td>${esc(x.body)}</td><td>${status(x.status)}</td></tr>`).join('')||'<tr><td colspan=4>No conversations yet.</td></tr>'}</table></section><section><h2>Attempts</h2><table><tr><th>Issue</th><th>Stage</th><th>Score</th><th>Model</th><th>Patch / PR</th><th>Notes</th></tr>${d.attempts.map(a=>`<tr><td><a href="https://github.com/${esc(a.repository)}/issues/${a.issue_number}" target=_blank>${esc(a.repository)}#${a.issue_number}</a></td><td>${status(a.status)}</td><td>${esc(a.score)}</td><td>${esc(a.provider||'—')}<br>${esc(a.model||'')}</td><td>${a.pr_url?`<a href="${esc(a.pr_url)}" target=_blank>Pull request</a>`:a.patch_path?'<span class=muted>Local patch saved</span>':'—'}</td><td>${esc(a.error||a.reasons||'')}</td></tr>`).join('')||'<tr><td colspan=6>No attempts yet.</td></tr>'}</table></section><section><h2>Recent validation commands</h2><table><tr><th>Issue</th><th>Command</th><th>Exit</th><th>Output</th></tr>${d.commands.map(x=>`<tr><td>${esc(x.repository)}#${x.issue_number}</td><td><code>${esc(x.command)}</code></td><td>${esc(x.exit_code)}</td><td><pre>${esc(x.output)}</pre></td></tr>`).join('')||'<tr><td colspan=4>No commands recorded yet.</td></tr>'}</table></section>`}async function load(){try{let d=await (await fetch('/api/status')).json();document.querySelector('#targetprogress').innerHTML='<h2>Targeted run progress</h2>'+(d.target_log?'<pre>'+esc(d.target_log)+'</pre>':'<div class=empty>No targeted run yet.</div>');render(d)}catch(e){document.querySelector('#app').textContent='Dashboard unavailable: '+e}}load();setInterval(load,10000)</script>"""

PROGRESS_SCRIPT="""<script>async function agentProgress(){try{let d=await (await fetch('/api/status')).json(),e=document.querySelector('#agentprogress');if(!e)return;let rows=(d.events||[]).filter(x=>!d.current||x.attempt_id===d.current.id);e.innerHTML='<h2>Current agent activity</h2>'+(rows.length?'<table><tr><th>Time</th><th>Stage</th><th>Detail</th></tr>'+rows.map(x=>`<tr><td>${x.created_at}</td><td>${x.stage}</td><td>${x.detail}</td></tr>`).join('')+'</table>':'<div class=empty>No agent actions yet.</div>')}catch(_){}}agentProgress();setInterval(agentProgress,3000)</script>"""

def _service(action:str) -> tuple[bool,str]:
    label="com.evanprogramming.good-samaritan"; domain=f"gui/{os.getuid()}"; plist=Path.home()/"Library/LaunchAgents"/f"{label}.plist"
    loaded=subprocess.run(["launchctl","print",domain+"/"+label],text=True,capture_output=True).returncode==0
    if action=="start" and loaded:return True,"Daemon is already running."
    if action=="stop" and not loaded:return True,"Daemon is already stopped."
    command=["launchctl","bootout",domain+"/"+label] if action=="stop" else ["launchctl","bootstrap",domain,str(plist)]
    result=subprocess.run(command,text=True,capture_output=True)
    return result.returncode==0,(result.stdout+result.stderr).strip() or ("stopped" if action=="stop" else "started")

def serve(database: Path, config: Path, host: str="127.0.0.1", port: int=8765) -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            path=urlparse(self.path).path
            if path=="/api/status":
                body=json.dumps(snapshot(database)).encode(); content_type="application/json"
            elif path=="/": body=(PAGE+PROGRESS_SCRIPT).encode(); content_type="text/html; charset=utf-8"
            else: self.send_error(404); return
            self.send_response(200);self.send_header("Content-Type",content_type);self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(body)
        def do_POST(self):
            path=urlparse(self.path).path; length=int(self.headers.get("Content-Length","0")); fields=dict(x.split("=",1) for x in self.rfile.read(length).decode().split("&") if "=" in x)
            if path in ("/api/service/start","/api/service/stop"):
                ok,message=_service(path.rsplit("/",1)[-1]);body=json.dumps({"ok":ok,"message":message}).encode()
            elif path=="/api/run-repository":
                repo=fields.get("repository","").replace("%2F","/").replace("%2f","/")
                if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repo):self.send_error(400,"Use owner/repository");return
                with (config.parent/"targeted-run.log").open("a") as log:
                    subprocess.Popen([sys.executable,"-m","good_samaritan.cli","run","--config",str(config),"--repository",repo,"--json"],cwd=config.parent,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                body=json.dumps({"ok":True,"message":f"Started a targeted contribution attempt for {repo}. Progress and errors are in targeted-run.log."}).encode()
            else:self.send_error(404);return
            self.send_response(200);self.send_header("Content-Type","application/json");self.end_headers();self.wfile.write(body)
    ThreadingHTTPServer((host,port),Handler).serve_forever()
