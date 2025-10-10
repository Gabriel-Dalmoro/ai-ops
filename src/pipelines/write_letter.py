from __future__ import annotations
from pathlib import Path
from typing import Optional
from loguru import logger

from src.agents.memory import Memory
from src.llm import LLM, truncate_by_tokens

# Conservative token budgets for free tiers
MAX_RESUME_TOKENS = 1200
MAX_JOBDESC_TOKENS = 1200


def _load_prompt_template() -> str:
    tmpl_path = Path("src/prompts/tasks/tailor_cover.md")
    return tmpl_path.read_text(encoding="utf-8")


def _render_prompt(
    tmpl: str, *, job_title: str, job_desc: str, resume_text: str, brand_voice: str
) -> str:
    # Simple string replacement (could later swap to jinja2)
    return (
        tmpl.replace("{{job_title}}", job_title)
        .replace("{{job_desc}}", job_desc)
        .replace("{{resume_text}}", resume_text)
        .replace("{{brand_voice}}", brand_voice)
    )


def run_write_letter(
    job_title: str,
    job_desc: str,
    resume_text: Optional[str] = None, # This is now mostly for debugging
    brand_voice: Optional[str] = None,
) -> dict:
    """
    Tailor v2: Uses Retrieval-Augmented Generation (RAG).
    It queries the 'resume_chunks' memory to find the most relevant
    parts of the resume for a given job description.
    """
    # --- MEMORY RETRIEVAL ---
    profile_mem = Memory("profile")
    resume_mem = Memory("resume_chunks") # Connect to our new smart memory

    # Resolve brand voice from memory if missing
    if not brand_voice:
        brand_voice = profile_mem.get("brand_voice") or "Concise, optimistic, systems-builder tone."

    # --- THIS IS THE KEY UPGRADE ---
    logger.info("Searching for relevant resume chunks based on job description...")
    # The job description is now a search query!
    relevant_chunks = resume_mem.similar(query=job_desc, k=3) 
    
    # We join the results into a single string for the prompt
    contextual_resume = "\n---\n".join([chunk[0] for chunk in relevant_chunks])
    logger.success(f"Found {len(relevant_chunks)} relevant chunks to use as context.")
    
    # Use the new contextual resume. We keep the original resume_text parameter as a potential override.
    final_resume_text = resume_text or contextual_resume
    # --- END OF UPGRADE ---

    # Token safety: truncate big inputs for free tiers
    final_resume_text = truncate_by_tokens(final_resume_text, MAX_RESUME_TOKENS)
    job_desc = truncate_by_tokens(job_desc, MAX_JOBDESC_TOKENS)

    # Build prompt
    tmpl = _load_prompt_template()
    prompt = _render_prompt(
        tmpl,
        job_title=job_title,
        job_desc=job_desc,
        resume_text=final_resume_text, # We use the new dynamically retrieved text
        brand_voice=brand_voice,
    )

    # Call LLM
    llm = LLM()
    cover_letter = llm.generate(prompt)

    # Guardrail: ensure minimal length; retry once if too short
    if len(cover_letter.strip()) < 400:
        logger.warning("Initial cover letter was too short, retrying with corrective prompt...")
        corrective = (
            "\n\n[System note: Your previous response was too short. "
            "Rewrite to ~300 words, keep it factual, include 3 bullet highlights, "
            "and maintain the given brand voice.]"
        )
        cover_letter = llm.generate(prompt + corrective)

    # Write artifacts
    safe_job_title = job_title.replace(" ", "_").replace("/", "_")
    out_dir = Path("out") / safe_job_title
    out_dir.mkdir(parents=True, exist_ok=True)

    cover_path = out_dir / "cover_letter.md"
    cover_path.write_text(cover_letter, encoding="utf-8")

    bullets_path = out_dir / "resume_bullets.md"
    # This is still a stub, we can make this an agent later
    bullets = [
        "- Built AI-driven automations and pipelines.",
        "- Experienced with Next.js, TypeScript, and FastAPI.",
        "- Multilingual: English, Portuguese, Spanish; learning French.",
    ]
    bullets_path.write_text("\n".join(bullets), encoding="utf-8")

    logger.info(f"Tailor v2 finished for {job_title}")

    return {
        "job_title": job_title,
        "artifacts": {
            "cover_letter_path": str(cover_path),
            "resume_bullets_path": str(bullets_path),
        },
        "used_memory": {
            "resume_chunks": len(relevant_chunks),
            "brand_voice": bool(brand_voice),
        },
    }