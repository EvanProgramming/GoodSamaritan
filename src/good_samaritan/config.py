from __future__ import annotations
import os, tomllib
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

class GitHubConfig(BaseModel):
    token: str = Field(default_factory=lambda: os.getenv("GOOD_SAMARITAN_GITHUB_TOKEN", "")); min_stars:int=100; active_days:int=30; max_repositories:int=10; max_issues_per_repository:int=10; languages:list[str]=Field(default_factory=list); repository_blacklist:list[str]=Field(default_factory=list); organization_blacklist:list[str]=Field(default_factory=list); allow_assigned:bool=False
class Limits(BaseModel): max_agent_steps:int=40; max_modified_files:int=12; max_diff_lines:int=1000; command_timeout_seconds:int=600; test_retries:int=3; daily_model_calls:int=100; daily_pr_limit:int=5; provider_cooldown_seconds:int=60; provider_min_interval_seconds:int=65
class Runtime(BaseModel): dry_run:bool=True; allow_submit:bool=False; allow_dependency_install:bool=False; daemon_interval_seconds:int=86400; model_retry_interval_seconds:int=900; database_path:Path=Path("good-samaritan.db"); work_directory:Path=Path("good-samaritan-work")
class Social(BaseModel): enabled:bool=False; max_issue_comments_per_day:int=3; allow_large_repositories:bool=False
class Models(BaseModel): priority:list[str]=Field(default_factory=lambda:["groq","gemini","openrouter"]); groq_model:str=""; gemini_model:str=""; openrouter_model:str=""
class Settings(BaseModel): github:GitHubConfig=Field(default_factory=GitHubConfig); limits:Limits=Field(default_factory=Limits); runtime:Runtime=Field(default_factory=Runtime); models:Models=Field(default_factory=Models); social:Social=Field(default_factory=Social); git_name:str=Field(default_factory=lambda:os.getenv("GOOD_SAMARITAN_GIT_NAME","Good Samaritan")); git_email:str=Field(default_factory=lambda:os.getenv("GOOD_SAMARITAN_GIT_EMAIL",""))
def load_settings(path: Path | None = None, **overrides: object) -> Settings:
    # A local .env is optional and deliberately gitignored. Existing process
    # environment always wins, which makes launchd/CI configuration possible.
    load_dotenv(override=False)
    data = tomllib.loads(path.read_text()) if path and path.exists() else {}
    # Environment values intentionally use explicit names so secrets never need
    # to be copied into TOML. They override TOML; explicit caller/CLI values win.
    env_map={
        "GOOD_SAMARITAN_GITHUB_TOKEN":("github","token",str), "GOOD_SAMARITAN_MIN_STARS":("github","min_stars",int), "GOOD_SAMARITAN_ACTIVE_DAYS":("github","active_days",int),
        "GOOD_SAMARITAN_MAX_REPOSITORIES":("github","max_repositories",int), "GOOD_SAMARITAN_MAX_ISSUES_PER_REPOSITORY":("github","max_issues_per_repository",int),
        "GOOD_SAMARITAN_MAX_AGENT_STEPS":("limits","max_agent_steps",int), "GOOD_SAMARITAN_MAX_MODIFIED_FILES":("limits","max_modified_files",int), "GOOD_SAMARITAN_MAX_DIFF_LINES":("limits","max_diff_lines",int),
        "GOOD_SAMARITAN_COMMAND_TIMEOUT_SECONDS":("limits","command_timeout_seconds",int), "GOOD_SAMARITAN_PROVIDER_MIN_INTERVAL_SECONDS":("limits","provider_min_interval_seconds",int), "GOOD_SAMARITAN_DRY_RUN":("runtime","dry_run",lambda v:v.lower() in ("1","true","yes","on")),
        "GOOD_SAMARITAN_ALLOW_SUBMIT":("runtime","allow_submit",lambda v:v.lower() in ("1","true","yes","on")), "GOOD_SAMARITAN_DATABASE_PATH":("runtime","database_path",Path),
        "GOOD_SAMARITAN_WORK_DIRECTORY":("runtime","work_directory",Path), "GOOD_SAMARITAN_DAEMON_INTERVAL_SECONDS":("runtime","daemon_interval_seconds",int), "GOOD_SAMARITAN_MODEL_RETRY_INTERVAL_SECONDS":("runtime","model_retry_interval_seconds",int),
        "GOOD_SAMARITAN_GIT_NAME":(None,"git_name",str), "GOOD_SAMARITAN_GIT_EMAIL":(None,"git_email",str),
        "GROQ_MODEL":("models","groq_model",str), "GEMINI_MODEL":("models","gemini_model",str), "OPENROUTER_MODEL":("models","openrouter_model",str),
    }
    for name,(section,key,convert) in env_map.items():
        if value:=os.getenv(name):
            if section is None:data[key]=convert(value)
            else:data.setdefault(section,{})[key]=convert(value)
    settings = Settings.model_validate(data)
    for dotted, value in overrides.items():
        if value is None: continue
        parent, attr = dotted.split("."); setattr(getattr(settings,parent),attr,value)
    return settings
