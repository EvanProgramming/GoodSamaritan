from pathlib import Path

from good_samaritan.testing import detect_commands, install_dependencies


class RecordingTools:
    def __init__(self, root: Path):
        self.root = root
        self.ran: list[str] = []

    def run(self, command: str):
        self.ran.append(command)
        return type("Result", (), {"exit_code": 0})()


def test_installs_python_dependencies_into_disposable_venv(tmp_path):
    (tmp_path / "requirements.txt").write_text("example-package==1.0\n")
    tools = RecordingTools(tmp_path)

    install_dependencies(tools)

    assert len(tools.ran) == 3
    assert ".good-samaritan-venv" in tools.ran[0]
    assert "pip install pytest" in tools.ran[1]
    assert "pip install -r requirements.txt" in tools.ran[2]


def test_node_install_disables_lifecycle_scripts(tmp_path):
    (tmp_path / "package-lock.json").write_text("{}")
    tools = RecordingTools(tmp_path)

    install_dependencies(tools)

    assert tools.ran[-1] == "npm ci --ignore-scripts"


def test_repository_without_test_framework_gets_diff_validation(tmp_path):
    assert detect_commands(tmp_path) == ["git diff --check"]
