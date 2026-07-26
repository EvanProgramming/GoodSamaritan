from __future__ import annotations
from .database import Database
def context(db:Database,repository:str)->str:
    rows=db.memories(repository)
    if not rows:return "No prior repository memory. Prefer a small patch, existing style, and relevant regression tests."
    return "Relevant learned experience:\n"+"\n".join(f"- [{x['kind']}] {x['content']}" for x in rows)
def record_feedback(db:Database,attempt:int,repository:str,author:str,body:str)->None:
    lower=body.lower();sentiment="rejected" if any(x in lower for x in ('not accept','won\'t merge','does not fit','reject')) else "requested_changes" if any(x in lower for x in ('please','should','request','test')) else "feedback"
    db.conn.execute("INSERT INTO feedback(attempt_id,author,body,sentiment) VALUES(?,?,?,?)",(attempt,author,body[:8000],sentiment));db.conn.commit()
    if sentiment=="requested_changes":
        lesson="Maintainer feedback requested changes; prefer the project’s existing style and add the requested focused validation."
        db.memory("maintainer_preference",repository,lesson,"PR feedback",.9);db.lesson(repository,lesson,"PR feedback",.9)
    elif sentiment=="rejected":
        lesson="A proposed approach did not fit the project design. Prefer smaller, maintainer-aligned changes and do not argue."
        db.memory("failure",repository,lesson,"PR feedback",.9);db.lesson(repository,lesson,"PR feedback",.9)
