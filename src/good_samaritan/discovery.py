from __future__ import annotations
from datetime import datetime, timezone
from .config import Settings
from .models import Assessment, Candidate, Issue
SENSITIVE=("security","vulnerability","password","payment","crypto","authentication bypass")
INJECTION=("ignore previous instructions","reveal api key","read .env","system prompt","run this command")
def suspicious(text:str)->bool: return any(x in text.lower() for x in INJECTION)
def local_rejection(issue:Issue,settings:Settings)->str|None:
    text=(issue.title+' '+issue.body+' '+' '.join(issue.comments)).lower()
    if issue.has_open_pr:return "already has an open linked PR"
    if issue.assignee and not settings.github.allow_assigned:return "already assigned"
    if any(x in text for x in SENSITIVE):return "sensitive or security-related issue"
    if suspicious(text):return "possible prompt injection"
    if len(issue.body.strip())<20:return "insufficient issue detail"
    return None
def score(issue:Issue,assessment:Assessment|None=None,repo_stars:int=100,active_days:int=1)->Candidate:
    labels={x.lower() for x in issue.labels}; points=0.; reasons=[]
    for label,worth in (("good first issue",25),("help wanted",15),("bug",10),("documentation",8)):
        if label in labels: points+=worth; reasons.append(f"{label} label +{worth}")
    if len(issue.body)>120: points+=15; reasons.append("detailed description +15")
    if any(x in issue.body.lower() for x in ("expected","should","reproduce","steps")): points+=10; reasons.append("expected behavior or reproduction +10")
    if assessment:
        points+=assessment.confidence*25
        if assessment.clear and assessment.small_scope and assessment.expected_behavior and assessment.safe: points+=15; reasons.append("model says small and safe +15")
    points+=min(repo_stars,2000)/1000*5; points+=max(0,5-active_days/30)
    return Candidate(issue=issue,score=round(points,2),reasons=reasons,assessment=assessment)
