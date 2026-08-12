from __future__ import annotations
import os, tomllib
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

class GitHubConfig(BaseModel):
    token: str = Field(default_factory=lambda: os.getenv("GOOD_SAMARITAN_GITHUB_TOKEN", "")); min_stars:int=3000; active_days:int=14; max_issue_age_days:int=14; max_repositories:int=20; max_issues_per_repository:int=10; max_repository_size_kb:int=3000000; languages:list[str]=Field(default_factory=list); repository_blacklist:list[str]=Field(default_factory=list); organization_blacklist:list[str]=Field(default_factory=list); allow_assigned:bool=False; retry_attempts:int=4; retry_base_seconds:int=2
class Limits(BaseModel): max_agent_steps:int=100; paid_model_max_agent_steps:int=40; recoverable_tool_retries:int=3; max_model_wait_retries:int=3; max_exploration_steps:int=16; minimum_assessment_confidence:float=.75; max_provider_wait_seconds:int=65; max_modified_files:int=12; max_diff_lines:int=1000; command_timeout_seconds:int=600; test_retries:int=3; daily_model_calls:int=100; daily_pr_limit:int=5; max_issue_assessments_per_run:int=5; provider_cooldown_seconds:int=60; provider_min_interval_seconds:int=65; provider_retry_rounds:int=2; provider_retry_delay_seconds:int=5
class Runtime(BaseModel): dry_run:bool=True; allow_submit:bool=False; allow_dependency_install:bool=False; daemon_interval_seconds:int=86400; model_retry_interval_seconds:int=900; max_contribution_attempts_per_cycle:int=3; database_path:Path=Path("good-samaritan.db"); work_directory:Path=Path("good-samaritan-work")
class Social(BaseModel): enabled:bool=False; max_issue_comments_per_day:int=3; allow_large_repositories:bool=False
class Models(BaseModel): priority:list[str]=Field(default_factory=lambda:["omniroute","groq","gemini","openrouter"]); groq_model:str=""; gemini_model:str=""; openrouter_model:str=""; deepseek_model:str=""; omniroute_model:str=""; omniroute_fallback_model:str="oc/big-pickle"; omniroute_base_url:str="http://localhost:20128/v1"
class Settings(BaseModel): github:GitHubConfig=Field(default_factory=GitHubConfig); limits:Limits=Field(default_factory=Limits); runtime:Runtime=Field(default_factory=Runtime); models:Models=Field(default_factory=Models); social:Social=Field(default_factory=Social); git_name:str=Field(default_factory=lambda:os.getenv("GOOD_SAMARITAN_GIT_NAME","Good Samaritan")); git_email:str=Field(default_factory=lambda:os.getenv("GOOD_SAMARITAN_GIT_EMAIL",""))
def load_settings(path: Path | None = None, **overrides: object) -> Settings:
    # A local .env is optional and deliberately gitignored. Existing process
    # environment always wins, which makes launchd/CI configuration possible.
    # A service configuration normally lives beside its private .env, rather
    # than in the caller's working directory (as is the case for launchd and
    # dashboard-triggered targeted runs).
    if path is not None:
        load_dotenv(path.parent / ".env", override=False)
    load_dotenv(override=False)
    data = tomllib.loads(path.read_text()) if path and path.exists() else {}
    # Environment values intentionally use explicit names so secrets never need
    # to be copied into TOML. They override TOML; explicit caller/CLI values win.
    env_map={
        "GOOD_SAMARITAN_GITHUB_TOKEN":("github","token",str), "GOOD_SAMARITAN_MIN_STARS":("github","min_stars",int), "GOOD_SAMARITAN_ACTIVE_DAYS":("github","active_days",int),
        "GOOD_SAMARITAN_MAX_REPOSITORIES":("github","max_repositories",int), "GOOD_SAMARITAN_MAX_ISSUES_PER_REPOSITORY":("github","max_issues_per_repository",int), "GOOD_SAMARITAN_MAX_ISSUE_AGE_DAYS":("github","max_issue_age_days",int), "GOOD_SAMARITAN_MAX_REPOSITORY_SIZE_KB":("github","max_repository_size_kb",int),
        "GOOD_SAMARITAN_MAX_AGENT_STEPS":("limits","max_agent_steps",int), "GOOD_SAMARITAN_PAID_MODEL_MAX_AGENT_STEPS":("limits","paid_model_max_agent_steps",int), "GOOD_SAMARITAN_RECOVERABLE_TOOL_RETRIES":("limits","recoverable_tool_retries",int), "GOOD_SAMARITAN_MAX_MODEL_WAIT_RETRIES":("limits","max_model_wait_retries",int), "GOOD_SAMARITAN_MAX_EXPLORATION_STEPS":("limits","max_exploration_steps",int), "GOOD_SAMARITAN_MINIMUM_ASSESSMENT_CONFIDENCE":("limits","minimum_assessment_confidence",float), "GOOD_SAMARITAN_MAX_PROVIDER_WAIT_SECONDS":("limits","max_provider_wait_seconds",int), "GOOD_SAMARITAN_MAX_MODIFIED_FILES":("limits","max_modified_files",int), "GOOD_SAMARITAN_MAX_DIFF_LINES":("limits","max_diff_lines",int),
        "GOOD_SAMARITAN_COMMAND_TIMEOUT_SECONDS":("limits","command_timeout_seconds",int), "GOOD_SAMARITAN_PROVIDER_MIN_INTERVAL_SECONDS":("limits","provider_min_interval_seconds",int), "GOOD_SAMARITAN_DRY_RUN":("runtime","dry_run",lambda v:v.lower() in ("1","true","yes","on")),
        "GOOD_SAMARITAN_ALLOW_SUBMIT":("runtime","allow_submit",lambda v:v.lower() in ("1","true","yes","on")), "GOOD_SAMARITAN_DATABASE_PATH":("runtime","database_path",Path),
        "GOOD_SAMARITAN_WORK_DIRECTORY":("runtime","work_directory",Path), "GOOD_SAMARITAN_DAEMON_INTERVAL_SECONDS":("runtime","daemon_interval_seconds",int), "GOOD_SAMARITAN_MODEL_RETRY_INTERVAL_SECONDS":("runtime","model_retry_interval_seconds",int),
        "GOOD_SAMARITAN_MAX_CONTRIBUTION_ATTEMPTS_PER_CYCLE":("runtime","max_contribution_attempts_per_cycle",int),
        "GOOD_SAMARITAN_GIT_NAME":(None,"git_name",str), "GOOD_SAMARITAN_GIT_EMAIL":(None,"git_email",str),
        "GROQ_MODEL":("models","groq_model",str), "GEMINI_MODEL":("models","gemini_model",str), "OPENROUTER_MODEL":("models","openrouter_model",str), "DEEPSEEK_MODEL":("models","deepseek_model",str), "OMNIROUTE_MODEL":("models","omniroute_model",str), "OMNIROUTE_FALLBACK_MODEL":("models","omniroute_fallback_model",str), "OMNIROUTE_BASE_URL":("models","omniroute_base_url",str),
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
