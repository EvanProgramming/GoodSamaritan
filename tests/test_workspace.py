import subprocess

from good_samaritan.workspace import Workspace


def test_clone_retries_transient_network_failure(tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setattr("good_samaritan.workspace.time.sleep",lambda _:None)
    def fake_run(*args,**kwargs):
        calls.append(args[0])
        if len(calls)==1:
            raise subprocess.CalledProcessError(128,args[0],stderr="error: RPC failed; early EOF")
        (tmp_path/"attempt-repo").mkdir(exist_ok=True)
        return subprocess.CompletedProcess(args[0],0,stdout="",stderr="")
    monkeypatch.setattr("good_samaritan.workspace.subprocess.run",fake_run)
    workspace=Workspace(tmp_path)
    # The fake command creates the expected target on the successful retry.
    target=workspace.clone("https://github.com/acme/project.git")
    assert len(calls)==2 and target.name=="repo"
