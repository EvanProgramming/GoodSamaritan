from __future__ import annotations
import json, os, time
import httpx
from pydantic import BaseModel
from .config import Settings
from .models import ModelReply
class ModelUnavailable(RuntimeError): pass
class ModelRouter:
    def __init__(self,settings:Settings,client:httpx.Client|None=None): self.settings=settings; self.client=client or httpx.Client(timeout=45); self.cooldowns:dict[str,float]={}; self.calls=0
    def _key(self,p:str)->str:return os.getenv(f"{p.upper()}_API_KEY", "")
    def available(self):return [p for p in self.settings.models.priority if self._key(p) and getattr(self.settings.models,f"{p}_model","")]
    def complete(self,prompt:str,role:str="analysis")->ModelReply:
        if self.calls>=self.settings.limits.daily_model_calls:raise ModelUnavailable("daily model call limit reached")
        errors=[]
        for p in self.settings.models.priority:
            if not self._key(p) or not getattr(self.settings.models,f"{p}_model","") or self.cooldowns.get(p,0)>time.monotonic():continue
            try:
                reply=self._call(p,prompt); self.calls+=1; return reply
            except (httpx.HTTPError,ValueError) as e:
                errors.append(f"{p}: {e}"); self.cooldowns[p]=time.monotonic()+self.settings.limits.provider_cooldown_seconds
        raise ModelUnavailable("all configured model providers unavailable: "+"; ".join(errors))
    def _call(self,p:str,prompt:str)->ModelReply:
        model=getattr(self.settings.models,f"{p}_model")
        if p=="gemini":
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self._key(p)}"; r=self.client.post(url,json={"contents":[{"parts":[{"text":prompt}]}]}); r.raise_for_status(); content=r.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            base="https://api.groq.com/openai/v1" if p=="groq" else "https://openrouter.ai/api/v1"; r=self.client.post(base+"/chat/completions",headers={"Authorization":f"Bearer {self._key(p)}"},json={"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0}); r.raise_for_status(); content=r.json()["choices"][0]["message"]["content"]
        return ModelReply(provider=p,model=model,content=content,estimated_tokens=max(1,len(prompt+content)//4))
    def structured(self,prompt:str,schema:type[BaseModel])->tuple[BaseModel,ModelReply]:
        reply=self.complete(prompt+"\nReturn only a JSON object matching this schema: "+json.dumps(schema.model_json_schema()))
        raw=reply.content.strip().removeprefix("```json").removesuffix("```").strip()
        return schema.model_validate_json(raw),reply
