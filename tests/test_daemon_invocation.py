from good_samaritan import cli


def test_daemon_passes_plain_run_parameters(monkeypatch, tmp_path):
    calls = []
    delays = []
    monkeypatch.setattr(cli, "settings", lambda _: type("S", (), {"runtime": type("R", (), {"database_path": tmp_path / "db.sqlite", "work_directory": tmp_path / "work", "allow_submit": False, "dry_run": True, "daemon_interval_seconds": 1, "model_retry_interval_seconds": 1})()})())
    monkeypatch.setattr(cli, "Database", lambda *_: type("DB", (), {"close": lambda self: None, "recover_abandoned": lambda self, **_: 0})())
    monkeypatch.setattr(cli, "cleanup_orphan_workspaces", lambda _: [])
    monkeypatch.setattr(cli, "generate_journal", lambda *_: (None, None))
    def run(**kwargs):
        calls.append(kwargs)
        return "MODEL_UNAVAILABLE"
    monkeypatch.setattr(cli, "run", run)
    monkeypatch.setattr(cli, "stopping", False)
    # Stop after the first cycle, before the sleep loop observes another one.
    def sleep(seconds):
        delays.append(seconds)
        setattr(cli, "stopping", True)
    monkeypatch.setattr(cli.time, "sleep", sleep)
    monkeypatch.setattr(cli, "GitHub", lambda _: object())
    monkeypatch.setattr(cli, "ModelRouter", lambda _: object())
    monkeypatch.setattr(cli, "follow_prs", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "process_remediation", lambda *args, **kwargs: False)

    cli.daemon(config=tmp_path / "config.toml")

    assert calls == [{"config": tmp_path / "config.toml", "submit": False, "repository": None, "json_output": False}]
    assert delays == [1]
