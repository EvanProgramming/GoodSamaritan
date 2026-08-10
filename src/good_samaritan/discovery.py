from __future__ import annotations
from datetime import datetime, timezone
import re
from .config import Settings
from .models import Assessment, Candidate, Issue
SENSITIVE=("security","vulnerability","password","payment","crypto","authentication bypass")
INJECTION=("ignore previous instructions","reveal api key","read .env","system prompt","run this command")
LINKED_PR=(
    re.compile(r"https?://github\.com/[^\s)]+/pull/\d+",re.I),
    re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+(?:this|the)\s+(?:issue|bug)\b",re.I),
    re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+(?:#\d+|[\w.-]+/[\w.-]+#\d+|https?://github\.com/[^\s)]+/(?:issues|pull)/\d+)\b",re.I),
    re.compile(r"\b(?:pull request|pull-request|pr)\b[^\n]{0,160}\b(?:will\s+)?(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b",re.I),
    re.compile(r"\b(?:#\d+|[\w.-]+/[\w.-]+#\d+|https?://github\.com/[^\s)]+/pull/\d+)\b[^\n]{0,120}\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b",re.I),
)
def linked_pr(text:str)->bool:return any(pattern.search(text) for pattern in LINKED_PR)
def suspicious(text:str)->bool: return any(x in text.lower() for x in INJECTION)
def local_rejection(issue:Issue,settings:Settings)->str|None:
    text=(issue.title+' '+issue.body+' '+' '.join(issue.comments)).lower()
    age=(datetime.now(timezone.utc)-issue.created_at).total_seconds()/86400
    if age>settings.github.max_issue_age_days:return f"issue is older than {settings.github.max_issue_age_days} days"
    if issue.has_open_pr or linked_pr(text):return "issue already links a PR or says a PR will close it"
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
