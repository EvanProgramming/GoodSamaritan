from good_samaritan.models import Issue, ModelReply
from good_samaritan.social import investigation_comment
class Router:
    def complete(self,prompt,role):
        self.prompt=prompt
        assert role=='social' and 'untrusted issue data' in prompt.lower()
        return ModelReply(provider='test',model='test',content='This repository has an interesting problem. I will investigate a small verified fix and open a PR only if validation succeeds. Thank you for maintaining it.')
def test_social_comment_uses_personality_prompt():
    router=Router();text=investigation_comment(router,Issue(repository='owner/repo',number=1,title='Bug',body='details'))
    assert 'interesting' in text and 'PR' in text and 'Created By @EvanProgramming.' in text
    assert 'immediately before its pr is created' in router.prompt.lower()
