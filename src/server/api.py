from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.pipelines.job_apply import run_job_apply_stub
from src.agents.memory import Memory

app = FastAPI()


# -------------------- Health --------------------
@app.get("/health")
def health():
    return {"ok": True, "message": "AI-ops environment is alive!"}


# -------------------- Memory models --------------------
class ResumeUpsert(BaseModel):
    resume_text: str

class BrandVoiceUpsert(BaseModel):
    brand_voice: str


# -------------------- Memory endpoints --------------------
@app.post("/memory/resume")
def save_resume(req: ResumeUpsert):
    mem = Memory("profile")
    mem.upsert("resume", req.resume_text, {"type": "resume"})
    return {"ok": True}

@app.get("/memory/resume")
def get_resume():
    mem = Memory("profile")
    text = mem.get("resume")
    if text is None:
        raise HTTPException(status_code=404, detail="No resume saved yet.")
    return {"resume_text": text}

@app.post("/memory/brand-voice")
def save_brand_voice(req: BrandVoiceUpsert):
    mem = Memory("profile")
    mem.upsert("brand_voice", req.brand_voice, {"type": "brand_voice"})
    return {"ok": True}

@app.get("/memory/brand-voice")
def get_brand_voice():
    mem = Memory("profile")
    text = mem.get("brand_voice")
    if text is None:
        raise HTTPException(status_code=404, detail="No brand voice saved yet.")
    return {"brand_voice": text}


# -------------------- Apply models --------------------
class JobApplicationRequest(BaseModel):
    job_title: str
    job_desc: str
    resume_text: Optional[str] = None
    brand_voice: Optional[str] = None


# -------------------- Apply endpoint --------------------
@app.post("/apply")
def apply(req: JobApplicationRequest):
    result = run_job_apply_stub(
        job_title=req.job_title,
        job_desc=req.job_desc,
        resume_text=req.resume_text,
        brand_voice=req.brand_voice,
    )
    return result