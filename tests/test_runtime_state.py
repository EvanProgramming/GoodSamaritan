from good_samaritan.runtime_state import consume_manual_run, read, request_manual_run, write

def test_runtime_state_round_trip(tmp_path):
    database=tmp_path/'state.db';write(database,'WAITING_FOR_MODEL','provider unavailable',900)
    state=read(database)
    assert state['state']=='WAITING_FOR_MODEL' and state['wait_seconds']==900 and 'updated_at' in state

def test_manual_run_request_is_queued_and_consumed(tmp_path):
    database=tmp_path/'state.db';request_manual_run(database)
    assert (tmp_path/'manual-run.request').exists()
    assert consume_manual_run(database)
    assert not consume_manual_run(database)
