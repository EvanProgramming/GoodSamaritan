from good_samaritan.agent import Action
from good_samaritan.config import load_settings
from good_samaritan.models import ModelReply
from good_samaritan.router import ModelRouter


def test_extracts_json_object_from_chatty_response():
    raw = "I will inspect it first.\n```json\n{\"tool\": \"list_files\", \"path\": \".\"}\n```"
    parsed = Action.model_validate_json(ModelRouter._json_object(raw))

    assert parsed.tool == "list_files"
    assert parsed.path == "."

def test_structured_selects_valid_action_after_appended_schema():
    router=ModelRouter(load_settings())
    router.complete=lambda prompt,**kwargs: ModelReply(
        provider="omniroute",model="auto/coding",
        content='{"properties":{"tool":{"type":"string"}}}{"tool":"search_text","query":"bot_games"}',
    )
    action,_=router.structured("inspect",Action)
    assert action.tool=="search_text" and action.query=="bot_games"
