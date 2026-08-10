import inspect
from good_samaritan.cli import run
from good_samaritan.models import Issue, ModelReply
from good_samaritan.social import investigation_comment

class Router:
    def complete(self,prompt,role):
        self.prompt=prompt
        assert role=='social' and 'untrusted issue data' in prompt.lower()
        return ModelReply(provider='test',model='test',content='This repository has an interesting problem. I will open the prepared PR for review. Thank you for maintaining it.')

def test_social_comment_uses_model_at_final_pre_pr_checkpoint():
    router=Router();text=investigation_comment(router,Issue(repository='owner/repo',number=1,title='Bug',body='details'))
    assert 'interesting' in text and 'PR' in text and 'Created By' not in text and 'EvanProgramming' not in text
    assert 'branch has already been pushed' in router.prompt.lower()

def test_social_comment_discards_model_scratch_work_and_uses_linked_attribution():
    router=Router()
    router.complete=lambda prompt,role: ModelReply(provider='test',model='test',content='''We need to draft this.

Potential comment:

Hi! Good Samaritan has prepared a focused change. Created By [@EvanProgramming](https://github.com/EvanProgramming) 🌱

Count: 31 words.''')
    text=investigation_comment(router,Issue(repository='owner/repo',number=1,title='Bug',body='details'))
    assert text.startswith('Hi!') and 'Potential comment' not in text and 'Count:' not in text
    assert 'Created By' not in text and 'EvanProgramming' not in text

def test_issue_notification_is_structurally_before_pr_creation():
    source=inspect.getsource(run)
    assert source.index('posted=gh.comment') < source.index('pr=gh.create_pr')
    assert source.index('except Exception:\n                if opening_comment_id is not None:') < source.index('db.status(attempt,Status.PR_CREATED')
