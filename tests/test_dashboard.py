from good_samaritan.database import Database
from good_samaritan.discovery import score
from good_samaritan.dashboard import PAGE, clear_targeted_log, snapshot, targeted_command
from good_samaritan.models import Issue, Status

def test_snapshot_exposes_activity_without_secrets(tmp_path):
    db=Database(tmp_path/'state.db');candidate=score(Issue(repository='owner/repo',number=4,title='Fix',body='Expected result with steps'))
    attempt=db.create(candidate);db.status(attempt,Status.TESTING,provider='gemini',model='model-x');db.command(attempt,'python -m pytest',0,'1 passed')
    data=snapshot(tmp_path/'state.db');db.close()
    assert data['current']['repository']=='owner/repo' and data['commands'][0]['exit_code']==0 and data['runtime']['state']=='UNKNOWN' and 'token' not in str(data).lower()


def test_dashboard_target_command_is_a_live_submission(tmp_path):
    command=targeted_command(tmp_path/'config.toml','owner/repository')
    assert command[-2:]==['--submit','--json']
    assert command[command.index('--repository')+1]=='owner/repository'

def test_clear_targeted_log_keeps_database_history(tmp_path):
    config=tmp_path/'config.toml';log=tmp_path/'targeted-run.log';log.write_text('old progress')
    clear_targeted_log(config)
    assert log.read_text()==''

def test_dashboard_exposes_autonomous_run_control():
    assert '/api/run-autonomous' in PAGE and 'Start autonomous contribution' in PAGE
