from __future__ import annotations
import httpx
from .config import Settings
from .models import Issue
class GitHubError(RuntimeError): pass
class GitHub:
    def __init__(self,settings:Settings,client:httpx.Client|None=None): self.settings=settings; self.client=client or httpx.Client(base_url="https://api.github.com",timeout=30,headers={"Accept":"application/vnd.github+json","Authorization":f"Bearer {settings.github.token}"} if settings.github.token else {"Accept":"application/vnd.github+json"})
    def _get(self,path:str,**params):
        r=self.client.get(path,params=params); 
        if r.status_code>=400: raise GitHubError(f"GitHub {r.status_code}: {r.text[:300]}")
        return r.json()
    def user(self): return self._get("/user")
    def discover(self):
        q=f"stars:>={self.settings.github.min_stars} pushed:>={__import__('datetime').date.today()-__import__('datetime').timedelta(days=self.settings.github.active_days)} archived:false fork:false"
        if self.settings.github.languages:q += " " + " ".join(f"language:{x}" for x in self.settings.github.languages)
        return self._get("/search/repositories",q=q,sort="updated",order="desc",per_page=self.settings.github.max_repositories)["items"]
    def issues(self,repo:str):
        rows=self._get(f"/repos/{repo}/issues",state="open",per_page=self.settings.github.max_issues_per_repository)
        return [Issue(repository=repo,number=x["number"],title=x["title"],body=x.get("body") or "",labels=[z["name"] for z in x["labels"]],assignee=(x.get("assignee")or{}).get("login")) for x in rows if "pull_request" not in x]
    def repo(self,repo:str):return self._get(f"/repos/{repo}")
    def fork(self,repo:str):
        r=self.client.post(f"/repos/{repo}/forks");
        if r.status_code not in (200,202):raise GitHubError(f"fork failed: {r.status_code} {r.text[:300]}")
        return r.json()
    def create_pr(self,repo:str,title:str,body:str,head:str,base:str):
        r=self.client.post(f"/repos/{repo}/pulls",json={"title":title,"body":body,"head":head,"base":base});
        if r.status_code>=300:raise GitHubError(f"PR failed: {r.status_code} {r.text[:300]}")
        return r.json()
