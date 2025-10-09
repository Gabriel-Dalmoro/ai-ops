from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from loguru import logger
import xxhash
from pypdf import PdfReader

from src.pipelines.job_apply import run_job_apply
from src.pipelines.rank_job import run_job_ranker
from src.agents.memory import Memory

app = FastAPI()

# --- Configuration ---
RESUME_PDF_PATH = "GabrielDalmoro_Resume_Software_2025.pdf"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
RANKING_THRESHOLD = 7.0 # <-- New: Our decision threshold

# -------------------- Health --------------------
@app.get("/health")
def health():
    return {"ok": True, "message": "AI-ops environment is alive!"}

# -------------------- Memory Models & Endpoints --------------------
class BrandVoiceUpsert(BaseModel):
    brand_voice: str

@app.post("/memory/brand-voice")
def save_brand_voice(req: BrandVoiceUpsert):
    mem = Memory("profile")
    mem.upsert("brand_voice", req.brand_voice, {"type": "brand_voice"})
    return {"ok": True}

@app.post("/memory/resume/index")
def index_resume():
    pdf_path = Path(RESUME_PDF_PATH)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"Resume PDF not found at {RESUME_PDF_PATH}")

    current_fingerprint = xxhash.xxh64(pdf_path.read_bytes()).hexdigest()
    profile_mem = Memory("profile")
    saved_fingerprint = profile_mem.get_resume_fingerprint()

    if current_fingerprint == saved_fingerprint:
        return {"ok": True, "message": "Resume memory is already up-to-date."}

    logger.info("New resume version detected. Starting indexing process...")
    reader = PdfReader(pdf_path)
    resume_text = "".join(page.extract_text() or "" for page in reader.pages)
    chunks = [resume_text[i:i + CHUNK_SIZE] for i in range(0, len(resume_text), CHUNK_SIZE - CHUNK_OVERLAP)]
    
    resume_mem = Memory("resume_chunks")
    doc_ids = [f"resume_chunk_{i}" for i in range(len(chunks))]
    resume_mem.col.upsert(ids=doc_ids, documents=chunks)
    profile_mem.set_resume_fingerprint(current_fingerprint)

    logger.success(f"Successfully indexed {len(chunks)} chunks and saved new fingerprint.")
    return {"ok": True, "message": f"Successfully indexed new resume with {len(chunks)} chunks."}

# -------------------- Orchestrator Endpoint --------------------
class JobProcessRequest(BaseModel):
    job_title: str
    job_desc: str

@app.post("/process-job")
def process_job_application(req: JobProcessRequest):
    """
    This is the main orchestrator. It chains the Ranker and Tailor agents.
    1. Ranks the job fit.
    2. If the fit is good enough, proceeds to generate a cover letter.
    3. Returns a full report of the process.
    """
    # Step 1: Delegate to the Ranker Agent
    logger.info(f"--- Starting Orchestrated Job Process for: {req.job_title} ---")
    ranking_result = run_job_ranker(job_title=req.job_title, job_desc=req.job_desc)
    fit_score = ranking_result.get("fit_score", 0.0)

    # Step 2: Make a Decision
    if fit_score < RANKING_THRESHOLD:
        logger.warning(f"Job ranked {fit_score}, which is below the threshold of {RANKING_THRESHOLD}. Halting process.")
        return {
            "status": "skipped",
            "ranking": ranking_result,
            "message": "Job fit was too low to proceed with application."
        }
    
    logger.success(f"Job ranked {fit_score}, proceeding to tailor application.")

    # Step 3: Delegate to the Tailor Agent
    application_result = run_job_apply(job_title=req.job_title, job_desc=req.job_desc)

    # Step 4: Return a full report
    return {
        "status": "processed",
        "ranking": ranking_result,
        "application_artifacts": application_result.get("artifacts"),
        "message": "Job processed successfully."
    }