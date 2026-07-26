from __future__ import annotations
import os, tomllib
from pathlib import Path
from pydantic import BaseModel, Field

class GitHubConfig(BaseModel):
    token: str = Field(default_factory=lambda: os.getenv("GOOD_SAMARITAN_GITHUB_TOKEN", "")); min_stars:int=100; active_days:int=30; max_repositories:int=10; max_issues_per_repository:int=10; languages:list[str]=Field(default_factory=list); repository_blacklist:list[str]=Field(default_factory=list); organization_blacklist:list[str]=Field(default_factory=list); allow_assigned:bool=False
class Limits(BaseModel): max_agent_steps:int=12; max_modified_files:int=5; max_diff_lines:int=300; command_timeout_seconds:int=120; test_retries:int=2; daily_model_calls:int=30; provider_cooldown_seconds:int=60
class Runtime(BaseModel): dry_run:bool=True; allow_submit:bool=False; daemon_interval_seconds:int=86400; database_path:Path=Path("good-samaritan.db"); work_directory:Path=Path("good-samaritan-work")
class Models(BaseModel): priority:list[str]=Field(default_factory=lambda:["groq","gemini","openrouter"]); groq_model:str=""; gemini_model:str=""; openrouter_model:str=""
class Settings(BaseModel): github:GitHubConfig=Field(default_factory=GitHubConfig); limits:Limits=Field(default_factory=Limits); runtime:Runtime=Field(default_factory=Runtime); models:Models=Field(default_factory=Models); git_name:str=Field(default_factory=lambda:os.getenv("GOOD_SAMARITAN_GIT_NAME","Good Samaritan")); git_email:str=Field(default_factory=lambda:os.getenv("GOOD_SAMARITAN_GIT_EMAIL",""))
def load_settings(path: Path | None = None, **overrides: object) -> Settings:
    data = tomllib.loads(path.read_text()) if path and path.exists() else {}
    settings = Settings.model_validate(data)
    for dotted, value in overrides.items():
        if value is None: continue
        parent, attr = dotted.split("."); setattr(getattr(settings,parent),attr,value)
    return settings
