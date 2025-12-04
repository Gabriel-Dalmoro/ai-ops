from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from loguru import logger
import xxhash
from pypdf import PdfReader

from src.pipelines.write_letter import run_write_letter
from src.pipelines.rank_job import run_job_ranker
from src.pipelines.track_job import run_job_tracker
from src.pipelines.scrape_job_url import run_url_scraper
from src.agents.memory import Memory

app = FastAPI()

# --- Configuration ---
RESUME_PDF_PATH = "GabrielDalmoro_Resume_Software_2025.pdf"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
RANKING_THRESHOLD = 7.0

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

# -------------------- Main Orchestrator Endpoints -------------------
class JobProcessRequest(BaseModel):
    job_title: str
    company: str
    job_desc: str
    job_url: str = ""

# --- NEW: The URL-based endpoint ---
class URLProcessRequest(BaseModel):
    job_url: str

@app.post("/process-job-from-url")
def process_job_from_url(req: URLProcessRequest):
    """
    The new top-level orchestrator. Takes a URL, scrapes it,
    then passes the data to the main processing logic.
    """
    # Step 1: Delegate to the Scraper Agent
    scraped_data = run_url_scraper(req.job_url)
    
    # --- VALIDATION ---
    if not scraped_data or not scraped_data.get("job_desc"):
        logger.error("Scraper returned invalid data (missing description). Halting pipeline.")
        raise HTTPException(
            status_code=400, 
            detail="Failed to extract valid job details. The URL might be a search page or blocked."
        )
    
    # Step 2: Call the existing job processing logic with the scraped data
    return process_job_application(JobProcessRequest(**scraped_data))


@app.post("/process-job")
def process_job_application(req: JobProcessRequest):
    """
    This is the main orchestrator. It chains the Ranker, Tailor, and Tracker agents.
    """
    logger.info(f"--- Starting Orchestrated Job Process for: {req.job_title} ---")
    
    ranking_result = run_job_ranker(job_title=req.job_title, job_desc=req.job_desc)
    fit_score = ranking_result.get("fit_score", 0.0)

    if fit_score < RANKING_THRESHOLD:
        logger.warning(f"Job ranked {fit_score}, below threshold. Halting and logging as 'Skipped'.")
        run_job_tracker(
            job_title=req.job_title,
            company=req.company,
            job_url=req.job_url,
            status="Skipped",
            fit_score=fit_score,
            reason=ranking_result.get("reason", ""),
            cover_letter_text="N/A - Job fit score was too low."
        )
        return {"status": "skipped", "ranking": ranking_result, "message": "Job fit too low. Logged to Notion as 'Skipped'."}
    
    logger.success(f"Job ranked {fit_score}, proceeding to write letter.")

    application_result = run_write_letter(job_title=req.job_title, job_desc=req.job_desc)
    
    cover_letter_path_str = application_result.get("artifacts", {}).get("cover_letter_path")
    cover_letter_text = "Error: Could not read cover letter file."
    if cover_letter_path_str:
        try:
            cover_letter_text = Path(cover_letter_path_str).read_text()
        except Exception as e:
            logger.error(f"Failed to read cover letter file: {e}")

    notion_page_id = run_job_tracker(
        job_title=req.job_title,
        company=req.company,
        job_url=req.job_url,
        status="Written Letter",
        fit_score=fit_score,
        reason=ranking_result.get("reason", ""),
        cover_letter_text=cover_letter_text
    )

    return {
        "status": "processed",
        "ranking": ranking_result,
        "notion_page_id": notion_page_id,
        "message": "Job processed successfully and logged to Notion as 'Written Letter'."
    }

# from dotenv import load_dotenv
# load_dotenv()

# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from typing import Optional
# from pathlib import Path
# from loguru import logger
# import xxhash
# from pypdf import PdfReader

# # --- Import all three pipelines ---
# from src.pipelines.write_letter import run_write_letter
# from src.pipelines.rank_job import run_job_ranker
# from src.pipelines.track_job import run_job_tracker # <-- IMPORT THE NEW TRACKER
# from src.agents.memory import Memory

# app = FastAPI()

# # --- Configuration ---
# RESUME_PDF_PATH = "GabrielDalmoro_Resume_Software_2025.pdf"
# CHUNK_SIZE = 800
# CHUNK_OVERLAP = 100
# RANKING_THRESHOLD = 7.0

# # -------------------- Health --------------------
# @app.get("/health")
# def health():
#     return {"ok": True, "message": "AI-ops environment is alive!"}

# # -------------------- Memory Models & Endpoints --------------------
# class BrandVoiceUpsert(BaseModel):
#     brand_voice: str

# @app.post("/memory/brand-voice")
# def save_brand_voice(req: BrandVoiceUpsert):
#     mem = Memory("profile")
#     mem.upsert("brand_voice", req.brand_voice, {"type": "brand_voice"})
#     return {"ok": True}

# @app.post("/memory/resume/index")
# def index_resume():
#     pdf_path = Path(RESUME_PDF_PATH)
#     if not pdf_path.exists():
#         raise HTTPException(status_code=404, detail=f"Resume PDF not found at {RESUME_PDF_PATH}")

#     current_fingerprint = xxhash.xxh64(pdf_path.read_bytes()).hexdigest()
#     profile_mem = Memory("profile")
#     saved_fingerprint = profile_mem.get_resume_fingerprint()

#     if current_fingerprint == saved_fingerprint:
#         return {"ok": True, "message": "Resume memory is already up-to-date."}

#     logger.info("New resume version detected. Starting indexing process...")
#     reader = PdfReader(pdf_path)
#     resume_text = "".join(page.extract_text() or "" for page in reader.pages)
#     chunks = [resume_text[i:i + CHUNK_SIZE] for i in range(0, len(resume_text), CHUNK_SIZE - CHUNK_OVERLAP)]
    
#     resume_mem = Memory("resume_chunks")
#     doc_ids = [f"resume_chunk_{i}" for i in range(len(chunks))]
#     resume_mem.col.upsert(ids=doc_ids, documents=chunks)
#     profile_mem.set_resume_fingerprint(current_fingerprint)

#     logger.success(f"Successfully indexed {len(chunks)} chunks and saved new fingerprint.")
#     return {"ok": True, "message": f"Successfully indexed new resume with {len(chunks)} chunks."}


# # -------------------- Orchestrator Endpoint --------------------
# class JobProcessRequest(BaseModel):
#     job_title: str
#     company: str 
#     job_desc: str
#     job_url: str = "" 

# @app.post("/process-job")
# def process_job_application(req: JobProcessRequest):
#     """
#     This is the main orchestrator. It chains the Ranker, Tailor, and Tracker agents.
#     """
#     logger.info(f"--- Starting Orchestrated Job Process for: {req.job_title} ---")
    
#     # Step 1: Delegate to the Ranker Agent
#     ranking_result = run_job_ranker(job_title=req.job_title, job_desc=req.job_desc)
#     fit_score = ranking_result.get("fit_score", 0.0)

#     # Step 2: Make a Decision
#     if fit_score < RANKING_THRESHOLD:
#         logger.warning(f"Job ranked {fit_score}, which is below the threshold. Halting process.")
#         # Even if we halt, we can still track the lead as "Skipped"
#         run_job_tracker(
#             job_title=req.job_title,
#             company=req.company,
#             job_url=req.job_url,
#             status="Skipped",
#             fit_score=fit_score,
#             reason=ranking_result.get("reason", ""),
#             cover_letter_text="N/A - Job fit score was too low."
#         )
#         return {"status": "skipped", "ranking": ranking_result, "message": "Job fit too low. Logged to Notion as 'Skipped'."}
    
#     logger.success(f"Job ranked {fit_score}, proceeding to tailor application.")

#     # Step 3: Delegate to the Tailor Agent
#     # We need to read the generated cover letter from the file to pass it to the tracker
#     application_result = run_write_letter(job_title=req.job_title, job_desc=req.job_desc)
#     cover_letter_path_str = application_result.get("artifacts", {}).get("cover_letter_path")
    
#     cover_letter_text = "Error: Could not read cover letter file."
#     if cover_letter_path_str:
#         try:
#             cover_letter_text = Path(cover_letter_path_str).read_text()
#         except Exception as e:
#             logger.error(f"Failed to read cover letter file at {cover_letter_path_str}: {e}")

#     # Step 4: Delegate to the Tracker Agent
#     notion_page_id = run_job_tracker(
#         job_title=req.job_title,
#         company=req.company,
#         job_url=req.job_url,
#         status="Written Letter",
#         fit_score=fit_score,
#         reason=ranking_result.get("reason", ""),
#         cover_letter_text=cover_letter_text
#     )

#     # Step 5: Return a full report
#     return {
#         "status": "processed",
#         "ranking": ranking_result,
#         "notion_page_id": notion_page_id,
#         "message": "Job processed successfully and logged to Notion."
#     }
