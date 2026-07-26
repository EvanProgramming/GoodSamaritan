from good_samaritan.agent import Action
from good_samaritan.router import ModelRouter


def test_extracts_json_object_from_chatty_response():
    raw = "I will inspect it first.\n```json\n{\"tool\": \"list_files\", \"path\": \".\"}\n```"
    parsed = Action.model_validate_json(ModelRouter._json_object(raw))

    assert parsed.tool == "list_files"
    assert parsed.path == "."
