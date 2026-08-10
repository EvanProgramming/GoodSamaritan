from pathlib import Path
from good_samaritan.database import Database
from good_samaritan.discovery import score
from good_samaritan.followup import follow_prs
from good_samaritan.models import Issue, Status

class FakeGitHub:
    def user(self): return {'login':'good-bot'}
    def pr(self,repo,number): return {'state':'open','mergeable_state':'clean','head':{'sha':'abc'}}
    def pr_reviews(self,repo,number): return [{'state':'CHANGES_REQUESTED'}]
    def check_runs(self,repo,sha): return [{'status':'completed','conclusion':'success'}]
    def pr_comments(self,repo,number): return [{'id':99,'body':'Please rename this function.','user':{'login':'maintainer'}},{'id':100,'body':'Thanks for the work.','user':{'login':'good-bot'}}]
    def issue_comments(self,repo,number): return [{'id':99,'body':'Please rename this function.','user':{'login':'maintainer'}}]
    def comment(self,*args): raise AssertionError('dry run must not write')

def test_followup_tracks_requested_changes_and_drafts_reply(tmp_path):
    db=Database(tmp_path/'state.db');candidate=score(Issue(repository='owner/repo',number=4,title='Fix',body='Expected result with steps'))
    attempt=db.create(candidate);db.status(attempt,Status.PR_CREATED,pr_url='https://github.com/owner/repo/pull/7')
    follow_prs(db,FakeGitHub(),submit=False)
    row=db.show(attempt);interaction=db.conn.execute('SELECT * FROM interactions').fetchone();pr=db.conn.execute('SELECT * FROM pr_status').fetchone();task=db.conn.execute('SELECT * FROM followup_tasks').fetchone();db.close()
    assert row['status']==Status.REVIEWING and pr['review_state']=='CHANGES_REQUESTED' and interaction['status']=='DRAFT' and task['kind']=='CHANGE_REQUEST'

def test_followup_never_replies_to_own_comment_or_duplicate_id(tmp_path):
    db=Database(tmp_path/'state.db');candidate=score(Issue(repository='owner/repo',number=4,title='Fix',body='Expected result with steps'))
    attempt=db.create(candidate);db.status(attempt,Status.PR_CREATED,pr_url='https://github.com/owner/repo/pull/7')
    follow_prs(db,FakeGitHub(),submit=False)
    assert db.conn.execute("SELECT COUNT(*) FROM interactions WHERE github_comment_id=100").fetchone()[0]==0
    assert db.conn.execute("SELECT COUNT(*) FROM interactions WHERE github_comment_id=99").fetchone()[0]==1
    db.close()
