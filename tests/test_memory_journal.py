from good_samaritan.database import Database
from good_samaritan.discovery import score
from good_samaritan.journal import generate
from good_samaritan.memory import context, record_feedback
from good_samaritan.models import Issue

def test_memory_is_recalled_for_same_repository(tmp_path):
    db=Database(tmp_path/'state.db');db.memory('project','owner/repo','Always add a regression test.','maintainer feedback',.9)
    assert 'regression test' in context(db,'owner/repo') and 'No prior' in context(db,'other/repo')
    db.close()
def test_feedback_creates_a_lesson(tmp_path):
    db=Database(tmp_path/'state.db');attempt=db.create(score(Issue(repository='owner/repo',number=1,title='Fix',body='Expected behavior and steps')))
    record_feedback(db,attempt,'owner/repo','maintainer','Please add a regression test.')
    assert db.lessons()[0]['repository']=='owner/repo';db.close()
def test_journal_writes_public_stats_without_secrets(tmp_path):
    db=Database(tmp_path/'state.db');attempt=db.create(score(Issue(repository='owner/repo',number=1,title='Fix',body='Expected behavior and steps')));db.contribution(attempt,'owner/repo',1,'Added a focused test.','Ready local patch')
    stats,report=generate(db,tmp_path/'website');db.close()
    assert stats.exists() and report.exists() and 'secret' not in stats.read_text().lower() and (tmp_path/'website'/'contributions'/'1.md').exists()
