from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from loguru import logger
import xxhash
from pydantic import BaseModel
from pypdf import PdfReader

from src.pipelines.job_apply import run_job_apply
from src.agents.memory import Memory

app = FastAPI()

# --- Configuration for the new indexer ---
RESUME_PDF_PATH = "GabrielDalmoro_Resume_Software_2025.pdf"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# -------------------- Health --------------------
@app.get("/health")
def health():
    return {"ok": True, "message": "AI-ops environment is alive!"}

# -------------------- Memory models --------------------
class ResumeUpsert(BaseModel):
    resume_text: str

class BrandVoiceUpsert(BaseModel):
    brand_voice: str

# -------------------- Simple Memory Endpoints --------------------
@app.post("/memory/brand-voice")
def save_brand_voice(req: BrandVoiceUpsert):
    mem = Memory("profile")
    mem.upsert("brand_voice", req.brand_voice, {"type": "brand_voice"})
    return {"ok": True}

# --- Smart Resume Indexing Endpoint ---
@app.post("/memory/resume/index")
def index_resume():
    """
    Checks if the resume PDF has changed via fingerprinting (hashing). 
    If so, it re-indexes it into the 'resume_chunks' collection.
    """
    pdf_path = Path(RESUME_PDF_PATH)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"Resume PDF not found at {RESUME_PDF_PATH}")

    current_fingerprint = xxhash.xxh64(pdf_path.read_bytes()).hexdigest()
    logger.info(f"Current resume fingerprint: {current_fingerprint}")

    profile_mem = Memory("profile")
    saved_fingerprint = profile_mem.get_resume_fingerprint()

    if current_fingerprint == saved_fingerprint:
        logger.info("Resume is already up-to-date. No indexing needed.")
        return {"ok": True, "message": "Resume memory is already up-to-date."}

    logger.info("New resume version detected. Starting indexing process...")
    
    reader = PdfReader(pdf_path)
    resume_text = "".join(page.extract_text() or "" for page in reader.pages)
    
    chunks = []
    for i in range(0, len(resume_text), CHUNK_SIZE - CHUNK_OVERLAP):
        chunks.append(resume_text[i:i + CHUNK_SIZE])
    
    logger.info(f"Split resume into {len(chunks)} chunks.")

    resume_mem = Memory("resume_chunks")
    doc_ids = [f"resume_chunk_{i}" for i in range(len(chunks))]
    
    resume_mem.col.upsert(ids=doc_ids, documents=chunks) # Using upsert is safe
    profile_mem.set_resume_fingerprint(current_fingerprint)

    logger.success(f"Successfully indexed {len(chunks)} chunks and saved new fingerprint.")
    return {"ok": True, "message": f"Successfully indexed new resume with {len(chunks)} chunks."}

# -------------------- Main Application Endpoint --------------------
class JobApplicationRequest(BaseModel):
    job_title: str
    job_desc: str
    resume_text: Optional[str] = None
    brand_voice: Optional[str] = None

@app.post("/apply")
def apply(req: JobApplicationRequest):
    result = run_job_apply(
        job_title=req.job_title,
        job_desc=req.job_desc,
        resume_text=req.resume_text,
        brand_voice=req.brand_voice,
    )
    return result



# from dotenv import load_dotenv
# load_dotenv()

# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from typing import Optional

# from src.pipelines.job_apply import run_job_apply
# from src.agents.memory import Memory

# app = FastAPI()

# # -------------------- Health --------------------
# @app.get("/health")
# def health():
#     return {"ok": True, "message": "AI-ops environment is alive!"}

# # -------------------- Memory models --------------------
# class ResumeUpsert(BaseModel):
#     resume_text: str

# class BrandVoiceUpsert(BaseModel):
#     brand_voice: str

# # -------------------- Memory endpoints --------------------
# @app.post("/memory/resume")
# def save_resume(req: ResumeUpsert):
#     mem = Memory("profile")
#     mem.upsert("resume", req.resume_text, {"type": "resume"})
#     return {"ok": True}

# @app.get("/memory/resume")
# def get_resume():
#     mem = Memory("profile")
#     text = mem.get("resume")
#     if text is None:
#         raise HTTPException(status_code=404, detail="No resume saved yet.")
#     return {"resume_text": text}

# @app.post("/memory/brand-voice")
# def save_brand_voice(req: BrandVoiceUpsert):
#     mem = Memory("profile")
#     mem.upsert("brand_voice", req.brand_voice, {"type": "brand_voice"})
#     return {"ok": True}

# @app.get("/memory/brand-voice")
# def get_brand_voice():
#     mem = Memory("profile")
#     text = mem.get("brand_voice")
#     if text is None:
#         raise HTTPException(status_code=404, detail="No brand voice saved yet.")
#     return {"brand_voice": text}

# # -------------------- Apply models --------------------
# class JobApplicationRequest(BaseModel):
#     job_title: str
#     job_desc: str
#     resume_text: Optional[str] = None
#     brand_voice: Optional[str] = None

# # -------------------- Apply endpoint --------------------
# @app.post("/apply")
# def apply(req: JobApplicationRequest):
#     result = run_job_apply(
#         job_title=req.job_title,
#         job_desc=req.job_desc,
#         resume_text=req.resume_text,
#         brand_voice=req.brand_voice,
#     )
#     return result