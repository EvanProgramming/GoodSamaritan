from good_samaritan.agent import Action, CodingAgent
from good_samaritan.config import Limits
from good_samaritan.models import ModelReply
from good_samaritan.router import ModelUnavailable
from good_samaritan.tools import SafeTools


class ScriptedRouter:
    def __init__(self):
        self.actions = iter([
            Action(tool="run_command", command="rm -rf not-allowed"),
            Action(tool="write_file", path="fix.txt", content="fixed\n"),
            Action(tool="finish"),
        ])

    def structured(self, *_):
        return next(self.actions), ModelReply(provider="test", model="test", content="{}")


def test_agent_recovers_from_rejected_command_and_continues(tmp_path):
    tools = SafeTools(tmp_path, Limits(max_agent_steps=4))
    result = CodingAgent(ScriptedRouter(), tools).run("Fix the defect")

    assert result == "{}"
    assert (tmp_path / "fix.txt").read_text() == "fixed\n"


class RepeatingRouter:
    def structured(self, *_):
        return Action(tool="read_file", path="README.md"), ModelReply(provider="test", model="test", content="{}")


def test_agent_stops_repeated_identical_actions_before_step_budget(tmp_path):
    (tmp_path / "README.md").write_text("guide")
    result=CodingAgent(RepeatingRouter(),SafeTools(tmp_path,Limits(max_agent_steps=20))).run("Fix the defect")
    assert result=="stopped: repeated identical tool action"

class BudgetRouter:
    def __init__(self,provider):
        self.provider=provider; self.last_provider=None; self.calls=0
    def structured(self, *_):
        self.last_provider=self.provider; self.calls+=1
        return Action(tool="read_file",path=f"file-{self.calls}.txt"), ModelReply(provider=self.provider,model="test",content="{}")

def test_agent_allows_100_steps_for_free_route(tmp_path):
    for index in range(1,101): (tmp_path/f"file-{index}.txt").write_text("ok")
    router=BudgetRouter("omniroute")
    result=CodingAgent(router,SafeTools(tmp_path,Limits(max_agent_steps=100))).run("Fix the defect")
    assert router.calls==100 and result=="stopped: agent step limit reached"

def test_agent_caps_paid_deepseek_route_at_40_steps(tmp_path):
    for index in range(1,101): (tmp_path/f"file-{index}.txt").write_text("ok")
    router=BudgetRouter("deepseek")
    result=CodingAgent(router,SafeTools(tmp_path,Limits(max_agent_steps=100,paid_model_max_agent_steps=40))).run("Fix the defect")
    assert router.calls==40 and result=="stopped: paid model step limit reached"

class RecoveringRouter:
    def __init__(self): self.calls=0
    def structured(self, *_):
        self.calls+=1
        if self.calls==1: raise ValueError("malformed action JSON")
        if self.calls==2:return Action(tool="write_file",path="fix.txt",content="fixed\n"),ModelReply(provider="test",model="test",content="{}")
        return Action(tool="finish"),ModelReply(provider="test",model="test",content="done")

def test_agent_retries_a_malformed_action_before_continuing(tmp_path):
    router=RecoveringRouter()
    result=CodingAgent(router,SafeTools(tmp_path,Limits(max_agent_steps=10,recoverable_tool_retries=3))).run("Fix the defect")
    assert result=="done" and (tmp_path/"fix.txt").read_text()=="fixed\n"

def test_agent_waits_and_resumes_when_model_api_is_temporarily_unavailable(tmp_path,monkeypatch):
    class TemporarilyUnavailable:
        def __init__(self):self.calls=0
        def structured(self,*_):
            self.calls+=1
            if self.calls==1:raise ModelUnavailable("all free providers unavailable")
            if self.calls==2:return Action(tool="write_file",path="fix.txt",content="fixed\n"),ModelReply(provider="omniroute",model="auto/coding",content="{}")
            return Action(tool="finish"),ModelReply(provider="omniroute",model="auto/coding",content="done")
    waits=[];resumes=[];monkeypatch.setattr("good_samaritan.agent.time.sleep",lambda _:None)
    router=TemporarilyUnavailable();result=CodingAgent(router,SafeTools(tmp_path,Limits(max_agent_steps=5))).run("Fix it",model_retry_interval=1,on_model_wait=lambda error,seconds:waits.append((error,seconds)),on_model_resume=lambda:resumes.append(True))
    assert result=="done" and router.calls==3 and waits and resumes and (tmp_path/"fix.txt").read_text()=="fixed\n"


def test_agent_bounds_provider_unavailability_waits(tmp_path,monkeypatch):
    class Unavailable:
        def structured(self,*_): raise ModelUnavailable("provider down")
    monkeypatch.setattr("good_samaritan.agent.time.sleep",lambda _:None)
    tools=SafeTools(tmp_path,Limits(max_agent_steps=20,max_model_wait_retries=2))
    try:
        CodingAgent(Unavailable(),tools).run("Fix it",model_retry_interval=1)
    except ModelUnavailable:
        pass
    else:
        raise AssertionError("provider outage should be bounded and surfaced")


def test_agent_bounds_rolling_tool_context(tmp_path):
    for index in range(1,11):
        (tmp_path/f"file-{index}.txt").write_text("x"*12000)
    class LargeOutputRouter:
        def __init__(self):self.calls=0;self.prompt_lengths=[];self.last_provider="omniroute"
        def structured(self,prompt,*_):
            self.calls+=1;self.prompt_lengths.append(len(prompt))
            if self.calls<=10:
                return Action(tool="read_file",path=f"file-{self.calls}.txt"),ModelReply(provider="omniroute",model="test",content="{}")
            if self.calls==11:return Action(tool="write_file",path="fix.txt",content="fixed\n"),ModelReply(provider="omniroute",model="test",content="{}")
            return Action(tool="finish"),ModelReply(provider="omniroute",model="test",content="done")
    router=LargeOutputRouter();result=CodingAgent(router,SafeTools(tmp_path,Limits(max_agent_steps=20))).run("Fix it")
    assert result=="done" and max(router.prompt_lengths)<=48000
