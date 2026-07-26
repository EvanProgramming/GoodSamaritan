from good_samaritan.agent import Action, CodingAgent
from good_samaritan.config import Limits
from good_samaritan.models import ModelReply
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
