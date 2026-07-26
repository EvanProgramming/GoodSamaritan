from good_samaritan.cleanup import cleanup_attempt_artifacts, cleanup_orphan_workspaces
from good_samaritan.database import Database

def test_cleanup_never_leaves_work_root(tmp_path):
    work=tmp_path/'work';(work/'attempt-a').mkdir(parents=True);(work/'attempt-a'/'x').write_text('x');(work/'keep').mkdir();(work/'attempt-7.patch').write_text('patch');(work/'attempt-7-pr.md').write_text('draft')
    assert len(cleanup_orphan_workspaces(work))==1 and (work/'keep').exists()
    assert len(cleanup_attempt_artifacts(work,7))==2


def test_immediate_recovery_resolves_an_interrupted_active_attempt(tmp_path):
    db=Database(tmp_path/'state.db')
    db.conn.execute("INSERT INTO attempts(repository,issue_number,status,score,reasons) VALUES(?,?,?,?,?)",('owner/repo',1,'EDITING',1,'test'))
    db.conn.commit()

    assert db.recover_abandoned(minutes=0)==1
    assert db.show(1)['status']=='FAILED'
    db.close()
