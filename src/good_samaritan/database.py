from __future__ import annotations
import sqlite3
from pathlib import Path
from .models import Candidate, Status
class Database:
    def __init__(self,path:Path): self.path=path; self.conn=sqlite3.connect(path); self.conn.row_factory=sqlite3.Row; self._init()
    def _init(self):
        self.conn.executescript("CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, repository TEXT, issue_number INTEGER, status TEXT, score REAL, reasons TEXT, provider TEXT, model TEXT, patch_path TEXT, pr_url TEXT, error TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(repository,issue_number)); CREATE TABLE IF NOT EXISTS commands(id INTEGER PRIMARY KEY, attempt_id INTEGER, command TEXT, exit_code INTEGER, output TEXT);")
    def seen(self, repo:str, number:int)->bool: return self.conn.execute("SELECT 1 FROM attempts WHERE repository=? AND issue_number=?",(repo,number)).fetchone() is not None
    def create(self,c:Candidate)->int:
        cur=self.conn.execute("INSERT INTO attempts(repository,issue_number,status,score,reasons) VALUES(?,?,?,?,?)",(c.issue.repository,c.issue.number,Status.SELECTED,c.score," | ".join(c.reasons))); self.conn.commit(); return cur.lastrowid
    def status(self,id:int,status:Status,**values:str):
        pairs={"status":status,**values}; sets=','.join(f'{k}=?' for k in pairs); self.conn.execute(f"UPDATE attempts SET {sets},updated_at=CURRENT_TIMESTAMP WHERE id=?",(*pairs.values(),id)); self.conn.commit()
    def command(self,id:int,command:str,code:int,output:str): self.conn.execute("INSERT INTO commands(attempt_id,command,exit_code,output) VALUES(?,?,?,?)",(id,command,code,output[:8000])); self.conn.commit()
    def history(self): return self.conn.execute("SELECT * FROM attempts ORDER BY id DESC").fetchall()
    def show(self,id:int): return self.conn.execute("SELECT * FROM attempts WHERE id=?",(id,)).fetchone()
    def close(self): self.conn.close()
