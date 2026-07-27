from __future__ import annotations
import time
import httpx
from .config import Settings
from .models import Issue
class GitHubError(RuntimeError): pass
class GitHub:
    def __init__(self,settings:Settings,client:httpx.Client|None=None): self.settings=settings; self.client=client or httpx.Client(base_url="https://api.github.com",timeout=30,headers={"Accept":"application/vnd.github+json","Authorization":f"Bearer {settings.github.token}"} if settings.github.token else {"Accept":"application/vnd.github+json"})
    def _delay(self,response:httpx.Response|None,attempt:int)->float:
        if response is not None:
            try:return max(0,float(response.headers.get("Retry-After","")))
            except ValueError:pass
        return self.settings.github.retry_base_seconds*(2**attempt)
    def _request(self,method:str,path:str,*,retry_transport:bool=True,**kwargs)->httpx.Response:
        retriable={429,500,502,503,504}; last=""
        for attempt in range(self.settings.github.retry_attempts):
            try:r=self.client.request(method,path,**kwargs)
            except httpx.TransportError as error:
                last=f"network error: {error}"
                if not retry_transport or attempt+1>=self.settings.github.retry_attempts:break
                time.sleep(self._delay(None,attempt));continue
            if r.status_code<400:return r
            last=f"GitHub {r.status_code} for {path}: {r.text[:300]}"
            if r.status_code not in retriable or attempt+1>=self.settings.github.retry_attempts:break
            time.sleep(self._delay(r,attempt))
        raise GitHubError(last or f"GitHub request failed for {path}")
    def _get(self,path:str,**params):
        return self._request("GET",path,params=params).json()
    def user(self): return self._get("/user")
    def discover(self):
        q=f"stars:>={self.settings.github.min_stars} pushed:>={__import__('datetime').date.today()-__import__('datetime').timedelta(days=self.settings.github.active_days)} archived:false fork:false"
        if self.settings.github.languages:q += " " + " ".join(f"language:{x}" for x in self.settings.github.languages)
        return self._get("/search/repositories",q=q,sort="updated",order="desc",per_page=self.settings.github.max_repositories)["items"]
    def issues(self,repo:str):
        rows=self._get(f"/repos/{repo}/issues",state="open",per_page=self.settings.github.max_issues_per_repository)
        issues=[]
        for item in rows:
            if "pull_request" in item:continue
            try: comments=[c.get("body") or "" for c in self.issue_comments(repo,item["number"])]
            except GitHubError: comments=[] # Some repositories disable issue comments.
            issues.append(Issue(repository=repo,number=item["number"],title=item["title"],body=item.get("body") or "",labels=[z["name"] for z in item["labels"]],comments=comments,assignee=(item.get("assignee")or{}).get("login")))
        return issues
    def issue_comments(self,repo:str,number:int):return self._get(f"/repos/{repo}/issues/{number}/comments",per_page=100)
    def pr(self,repo:str,number:int):return self._get(f"/repos/{repo}/pulls/{number}")
    def pr_reviews(self,repo:str,number:int):return self._get(f"/repos/{repo}/pulls/{number}/reviews",per_page=100)
    def pr_comments(self,repo:str,number:int):return self._get(f"/repos/{repo}/issues/{number}/comments",per_page=100)
    def check_runs(self,repo:str,ref:str):return self._get(f"/repos/{repo}/commits/{ref}/check-runs",per_page=100).get("check_runs",[])
    def comment(self,repo:str,number:int,body:str):
        return self._request("POST",f"/repos/{repo}/issues/{number}/comments",json={"body":body},retry_transport=False).json()
    def repo(self,repo:str):return self._get(f"/repos/{repo}")
    def fork(self,repo:str):
        r=self._request("POST",f"/repos/{repo}/forks",retry_transport=False)
        if r.status_code not in (200,202):raise GitHubError(f"fork failed: {r.status_code} {r.text[:300]}")
        return r.json()
    def create_pr(self,repo:str,title:str,body:str,head:str,base:str):
        return self._request("POST",f"/repos/{repo}/pulls",json={"title":title,"body":body,"head":head,"base":base},retry_transport=False).json()
