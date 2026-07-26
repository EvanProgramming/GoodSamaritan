from good_samaritan.config import load_settings

def test_classic_token_is_loaded_from_environment(monkeypatch):
    monkeypatch.setenv("GOOD_SAMARITAN_GITHUB_TOKEN", "ghp_example")
    assert load_settings().github.token.startswith("ghp_")
