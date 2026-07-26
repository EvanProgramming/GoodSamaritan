from good_samaritan.database import Database
from good_samaritan.discovery import score
from good_samaritan.dashboard import snapshot
from good_samaritan.models import Issue, Status

def test_snapshot_exposes_activity_without_secrets(tmp_path):
    db=Database(tmp_path/'state.db');candidate=score(Issue(repository='owner/repo',number=4,title='Fix',body='Expected result with steps'))
    attempt=db.create(candidate);db.status(attempt,Status.TESTING,provider='gemini',model='model-x');db.command(attempt,'python -m pytest',0,'1 passed')
    data=snapshot(tmp_path/'state.db');db.close()
    assert data['current']['repository']=='owner/repo' and data['commands'][0]['exit_code']==0 and 'token' not in str(data).lower()
