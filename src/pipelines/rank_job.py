from __future__ import annotations
from pathlib import Path
import json
from loguru import logger

from src.agents.memory import Memory
from src.llm import LLM, truncate_by_tokens

# --- Configuration ---
MAX_RESUME_TOKENS = 1500
MAX_JOBDESC_TOKENS = 1500

# --- NEW: A helper function to clean the AI's output ---
def _clean_json_response(text: str) -> str:
    """
    Cleans the raw text response from an LLM to extract a valid JSON object.
    It removes markdown code fences and leading/trailing whitespace.
    """
    # Find the start of the JSON object
    json_start_index = text.find('{')
    # Find the end of the JSON object
    json_end_index = text.rfind('}')
    
    if json_start_index != -1 and json_end_index != -1:
        # Extract the JSON part
        json_str = text[json_start_index:json_end_index + 1]
        return json_str
    
    # Fallback if no JSON object is found
    return text.strip()

def _load_prompt_template() -> str:
    tmpl_path = Path("src/prompts/tasks/rank_job_fit.md")
    return tmpl_path.read_text(encoding="utf-8")

def _render_prompt(tmpl: str, *, job_title: str, job_desc: str, resume_text: str) -> str:
    return (
        tmpl.replace("{{job_title}}", job_title)
        .replace("{{job_desc}}", job_desc)
        .replace("{{resume_text}}", resume_text)
    )

def run_job_ranker(job_title: str, job_desc: str) -> dict:
    logger.info(f"Starting job ranking for: {job_title}")
    
    resume_mem = Memory("resume_chunks")
    relevant_chunks = resume_mem.similar(query=job_desc, k=4)
    contextual_resume = "\n---\n".join([chunk[0] for chunk in relevant_chunks])
    
    if not relevant_chunks:
        logger.warning("Could not find any relevant resume chunks.")
    else:
        logger.success(f"Found {len(relevant_chunks)} relevant resume chunks.")

    safe_resume_text = truncate_by_tokens(contextual_resume, MAX_RESUME_TOKENS)
    safe_job_desc = truncate_by_tokens(job_desc, MAX_JOBDESC_TOKENS)

    prompt_template = _load_prompt_template()
    prompt = _render_prompt(
        tmpl=prompt_template, job_title=job_title, job_desc=safe_job_desc, resume_text=safe_resume_text
    )

    llm = LLM()
    response_text = llm.generate(prompt)
    logger.debug(f"LLM Response (raw):\n---\n{response_text}\n---")
    
    # --- UPDATED: Use the cleaner before parsing ---
    cleaned_text = _clean_json_response(response_text)
    
    try:
        result = json.loads(cleaned_text)
        logger.success("Successfully parsed JSON response from LLM.")
    except json.JSONDecodeError:
        logger.error(f"Failed to parse cleaned JSON. Cleaned text was: {cleaned_text}")
        result = {"fit_score": 0.0, "reason": "Error: Failed to get a valid analysis from the AI."}

    return result

