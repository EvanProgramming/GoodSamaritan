from __future__ import annotations
import sqlite3
from pathlib import Path
from .models import Candidate, Status
class Database:
    def __init__(self,path:Path): self.path=path; self.conn=sqlite3.connect(path); self.conn.row_factory=sqlite3.Row; self._init()
    def _init(self):
        self.conn.executescript("CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, repository TEXT, issue_number INTEGER, status TEXT, score REAL, reasons TEXT, provider TEXT, model TEXT, patch_path TEXT, pr_url TEXT, error TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(repository,issue_number)); CREATE TABLE IF NOT EXISTS commands(id INTEGER PRIMARY KEY, attempt_id INTEGER, command TEXT, exit_code INTEGER, output TEXT); CREATE TABLE IF NOT EXISTS pr_status(attempt_id INTEGER PRIMARY KEY, state TEXT, mergeable_state TEXT, review_state TEXT, checks_state TEXT, details TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS interactions(id INTEGER PRIMARY KEY, attempt_id INTEGER, github_comment_id INTEGER, kind TEXT, author TEXT, body TEXT, reply TEXT, status TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(attempt_id, github_comment_id, kind)); CREATE TABLE IF NOT EXISTS contributions(id INTEGER PRIMARY KEY,attempt_id INTEGER UNIQUE,repository TEXT,issue_number INTEGER,summary TEXT,status TEXT,pr_url TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY,kind TEXT,repository TEXT,content TEXT,source TEXT,confidence REAL DEFAULT 0.7,created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,attempt_id INTEGER,author TEXT,body TEXT,sentiment TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS lessons(id INTEGER PRIMARY KEY,repository TEXT,content TEXT,source TEXT,confidence REAL DEFAULT 0.7,created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS followup_tasks(id INTEGER PRIMARY KEY,attempt_id INTEGER,github_comment_id INTEGER UNIQUE,kind TEXT,feedback TEXT,status TEXT DEFAULT 'PENDING',result TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS attempt_events(id INTEGER PRIMARY KEY,attempt_id INTEGER,stage TEXT,detail TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);")
    def seen(self, repo:str, number:int)->bool: return self.conn.execute("SELECT 1 FROM attempts WHERE repository=? AND issue_number=?",(repo,number)).fetchone() is not None
    def create(self,c:Candidate)->int:
        cur=self.conn.execute("INSERT INTO attempts(repository,issue_number,status,score,reasons) VALUES(?,?,?,?,?)",(c.issue.repository,c.issue.number,Status.SELECTED,c.score," | ".join(c.reasons))); self.conn.commit(); return cur.lastrowid
    def status(self,id:int,status:Status,**values:str):
        pairs={"status":status,**values}; sets=','.join(f'{k}=?' for k in pairs); self.conn.execute(f"UPDATE attempts SET {sets},updated_at=CURRENT_TIMESTAMP WHERE id=?",(*pairs.values(),id)); self.conn.commit()
    def command(self,id:int,command:str,code:int,output:str): self.conn.execute("INSERT INTO commands(attempt_id,command,exit_code,output) VALUES(?,?,?,?)",(id,command,code,output[:8000])); self.conn.commit()
    def pr_state(self,id:int,**state:str):
        self.conn.execute("INSERT INTO pr_status(attempt_id,state,mergeable_state,review_state,checks_state,details) VALUES(?,?,?,?,?,?) ON CONFLICT(attempt_id) DO UPDATE SET state=excluded.state,mergeable_state=excluded.mergeable_state,review_state=excluded.review_state,checks_state=excluded.checks_state,details=excluded.details,updated_at=CURRENT_TIMESTAMP",(id,state.get("state",""),state.get("mergeable_state",""),state.get("review_state",""),state.get("checks_state",""),state.get("details","")));self.conn.commit()
    def interaction(self,attempt_id:int,comment_id:int,kind:str,author:str,body:str,reply:str="",status:str="SEEN"):
        self.conn.execute("INSERT OR IGNORE INTO interactions(attempt_id,github_comment_id,kind,author,body,reply,status) VALUES(?,?,?,?,?,?,?)",(attempt_id,comment_id,kind,author,body[:8000],reply[:8000],status));self.conn.commit()
    def responded(self,attempt_id:int,comment_id:int,kind:str)->bool:return self.conn.execute("SELECT 1 FROM interactions WHERE attempt_id=? AND github_comment_id=? AND kind=? AND status='REPLIED'",(attempt_id,comment_id,kind)).fetchone() is not None
    def daily_interactions(self,kind:str)->int:return self.conn.execute("SELECT COUNT(*) FROM interactions WHERE kind=? AND date(created_at)=date('now')",(kind,)).fetchone()[0]
    def daily_prs(self)->int:return self.conn.execute("SELECT COUNT(*) FROM attempts WHERE pr_url IS NOT NULL AND date(updated_at)=date('now')").fetchone()[0]
    def followup_task(self,attempt_id:int,comment_id:int,kind:str,feedback:str):self.conn.execute("INSERT OR IGNORE INTO followup_tasks(attempt_id,github_comment_id,kind,feedback) VALUES(?,?,?,?)",(attempt_id,comment_id,kind,feedback[:8000]));self.conn.commit()
    def pending_followups(self):return self.conn.execute("SELECT t.*,a.repository,a.issue_number,a.pr_url FROM followup_tasks t JOIN attempts a ON a.id=t.attempt_id WHERE t.status='PENDING' ORDER BY t.id LIMIT 1").fetchall()
    def finish_followup(self,id:int,status:str,result:str):self.conn.execute("UPDATE followup_tasks SET status=?,result=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(status,result[:8000],id));self.conn.commit()
    def event(self,attempt_id:int,stage:str,detail:str):self.conn.execute("INSERT INTO attempt_events(attempt_id,stage,detail) VALUES(?,?,?)",(attempt_id,stage,detail[:2000]));self.conn.commit()
    def memory(self,kind:str,repository:str,content:str,source:str,confidence:float=.7):self.conn.execute("INSERT INTO memories(kind,repository,content,source,confidence) VALUES(?,?,?,?,?)",(kind,repository,content[:4000],source,confidence));self.conn.commit()
    def memories(self,repository:str,limit:int=12):return self.conn.execute("SELECT * FROM memories WHERE repository=? OR repository='' ORDER BY confidence DESC, id DESC LIMIT ?",(repository,limit)).fetchall()
    def lesson(self,repository:str,content:str,source:str,confidence:float=.7):self.conn.execute("INSERT INTO lessons(repository,content,source,confidence) VALUES(?,?,?,?)",(repository,content[:4000],source,confidence));self.conn.commit()
    def lessons(self,limit:int=20):return self.conn.execute("SELECT * FROM lessons ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    def contribution(self,attempt_id:int,repository:str,issue_number:int,summary:str,status:str,pr_url:str=""):
        self.conn.execute("INSERT INTO contributions(attempt_id,repository,issue_number,summary,status,pr_url) VALUES(?,?,?,?,?,?) ON CONFLICT(attempt_id) DO UPDATE SET status=excluded.status,pr_url=excluded.pr_url,summary=excluded.summary,updated_at=CURRENT_TIMESTAMP",(attempt_id,repository,issue_number,summary[:4000],status,pr_url));self.conn.commit()
    def statistics(self):
        q=lambda sql:self.conn.execute(sql).fetchone()[0]
        return {"repositories_explored":q("SELECT COUNT(DISTINCT repository) FROM attempts"),"issues_reviewed":q("SELECT COUNT(*) FROM attempts"),"issues_attempted":q("SELECT COUNT(*) FROM attempts WHERE status NOT IN ('DISCOVERED','SKIPPED')"),"pull_requests":q("SELECT COUNT(*) FROM attempts WHERE pr_url IS NOT NULL"),"merged":q("SELECT COUNT(*) FROM pr_status WHERE state='closed' AND mergeable_state='merged'"),"rejected":q("SELECT COUNT(*) FROM attempts WHERE status='FAILED'"),"lessons":q("SELECT COUNT(*) FROM lessons"),"feedback":q("SELECT COUNT(*) FROM feedback")}
    def history(self): return self.conn.execute("SELECT * FROM attempts ORDER BY id DESC").fetchall()
    def recover_abandoned(self, minutes:int=15)->int:
        active=("SELECTED","CLONING","ANALYZING","EDITING","TESTING","REVIEWING")
        placeholders=','.join('?' for _ in active)
        query=f"UPDATE attempts SET status=?,error=?,updated_at=CURRENT_TIMESTAMP WHERE status IN ({placeholders})"
        values=("FAILED","Run interrupted before completion; safe recovery on daemon start.",*active)
        if minutes>0:
            query+=" AND updated_at < datetime('now', ?)";values=(*values,f"-{minutes} minutes")
        cur=self.conn.execute(query,values);self.conn.commit();return cur.rowcount
    def show(self,id:int): return self.conn.execute("SELECT * FROM attempts WHERE id=?",(id,)).fetchone()
    def close(self): self.conn.close()
