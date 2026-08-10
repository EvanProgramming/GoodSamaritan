from __future__ import annotations
from .database import Database
from .github import GitHub
from .models import Status
from .discovery import suspicious
from .memory import record_feedback
from .cleanup import cleanup_attempt_artifacts
from .social import reply_to_comment
from .router import ModelRouter, ModelUnavailable

def _pr_number(url:str)->int:return int(url.rstrip('/').split('/')[-1])
def _review_state(reviews:list[dict])->str:
    states=[r.get('state','').upper() for r in reviews]
    if 'CHANGES_REQUESTED' in states:return 'CHANGES_REQUESTED'
    if 'APPROVED' in states:return 'APPROVED'
    return 'PENDING_REVIEW'
def _needs_change(text:str)->bool:return any(word in text.lower() for word in ("please ","please add","please change","please update","please fix","should ","could you","needs a test","rename ","regression test"))
def follow_prs(db:Database,gh:GitHub,router:ModelRouter|None=None,submit:bool=False)->None:
    """Track every created PR; only post concise, deduplicated replies live."""
    me=gh.user().get('login','')
    for row in db.history():
        if not row['pr_url']:continue
        number=_pr_number(row['pr_url']);repo=row['repository'];pr=gh.pr(repo,number);reviews=gh.pr_reviews(repo,number);checks=gh.check_runs(repo,pr['head']['sha'])
        review=_review_state(reviews);check_state='FAILING' if any(c.get('conclusion') in ('failure','timed_out','cancelled') for c in checks) else 'PENDING' if any(c.get('status')!='completed' for c in checks) else 'PASSING'
        details=f"PR {pr.get('state')} · mergeable: {pr.get('mergeable_state') or 'unknown'} · review: {review} · checks: {check_state}"
        db.pr_state(row['id'],state=pr.get('state',''),mergeable_state=pr.get('mergeable_state') or 'unknown',review_state=review,checks_state=check_state,details=details)
        if pr.get('state')=='closed':
            outcome='Merged' if pr.get('merged_at') else 'Closed without merge'
            db.contribution(row['id'],repo,row['issue_number'],"Contribution lifecycle completed.",outcome,row['pr_url'])
            cleanup_attempt_artifacts(db.path.parent/'good-samaritan-work',row['id'])
        if review=='CHANGES_REQUESTED':db.status(row['id'],Status.REVIEWING,error='Maintainer requested changes; remediation is required before merge.')
        comments=gh.pr_comments(repo,number)+gh.issue_comments(repo,row['issue_number'])
        unique_comments={comment.get('id'):comment for comment in comments if comment.get('id') is not None}
        for comment in unique_comments.values():
            author=(comment.get('user') or {}).get('login','')
            body=comment.get('body') or '';cid=comment['id']
            # A bot may be addressed through a different login casing, and a
            # restarted database may not know about every old self-comment.
            # Never feed a self-authored or previously generated reply back to
            # the model; doing so is exactly the spam loop we want to prevent.
            if not author or author.casefold()==me.casefold():continue
            if (comment.get('author_association') or '').upper()=='BOT':continue
            if suspicious(body):db.interaction(row['id'],cid,'pr_comment',author,body,status='BLOCKED');continue
            if db.is_recorded_own_reply(row['id'],body):continue
            if db.responded_to_any_kind(row['id'],cid):continue
            record_feedback(db,row['id'],repo,author,body)
            change=_needs_change(body)
            if change:db.followup_task(row['id'],cid,'CHANGE_REQUEST',body)
            try:reply=reply_to_comment(router,body,author) if router else "Thanks for the feedback. Good Samaritan will evaluate it carefully and keep the contribution within the project’s expectations."
            except ModelUnavailable:reply="Thanks for the feedback. Good Samaritan will evaluate it carefully and keep the contribution within the project’s expectations."
            db.interaction(row['id'],cid,'pr_comment',author,body,reply,'REPLIED' if submit else 'DRAFT')
            if submit:gh.comment(repo,number,reply)
