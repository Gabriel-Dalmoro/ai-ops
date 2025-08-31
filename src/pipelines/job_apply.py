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


def run_job_apply(
    job_title: str,
    job_desc: str,
    resume_text: Optional[str] = None,
    brand_voice: Optional[str] = None,
) -> dict:
    """
    Tailor v1: builds a prompt from job + resume (+ brand voice),
    calls the LLM adapter with token guardrails, writes artifacts.
    Falls back to memory for resume/voice when not provided.
    """
    profile = Memory("profile")

    # Resolve resume and voice from memory if missing
    if not resume_text:
        resume_text = profile.get("resume") or "[No resume on file yet]"
    if not brand_voice:
        brand_voice = profile.get("brand_voice") or "Concise, optimistic, systems-builder tone."

    # Token safety: truncate big inputs for free tiers
    resume_text = truncate_by_tokens(resume_text, MAX_RESUME_TOKENS)
    job_desc = truncate_by_tokens(job_desc, MAX_JOBDESC_TOKENS)

    # Build prompt
    tmpl = _load_prompt_template()
    prompt = _render_prompt(
        tmpl,
        job_title=job_title,
        job_desc=job_desc,
        resume_text=resume_text,
        brand_voice=brand_voice,
    )

    # Call LLM (stub by default)
    llm = LLM()
    cover_letter = llm.generate(prompt)

    # Guardrail: ensure minimal length; retry once if too short
    if len(cover_letter.strip()) < 400:
        corrective = (
            "\n\n[System note: Your previous response was too short. "
            "Rewrite to ~300 words, keep it factual, include 3 bullet highlights, "
            "and maintain the given brand voice.]"
        )
        cover_letter = llm.generate(prompt + corrective)

    # Write artifacts
    out_dir = Path("out") / job_title.replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    cover_path = out_dir / "cover_letter.md"
    cover_path.write_text(cover_letter, encoding="utf-8")

    bullets_path = out_dir / "resume_bullets.md"
    bullets = [
        "- Built AI-driven automations and pipelines.",
        "- Experienced with Next.js, TypeScript, and FastAPI.",
        "- Multilingual: English, Portuguese, Spanish; learning French.",
    ]
    bullets_path.write_text("\n".join(bullets), encoding="utf-8")

    logger.info(f"Tailor v1 finished for {job_title}")

    return {
        "job_title": job_title,
        "artifacts": {
            "cover_letter_path": str(cover_path),
            "resume_bullets_path": str(bullets_path),
        },
        "used_memory": {
            "resume": bool(resume_text and resume_text != "[No resume on file yet]"),
            "brand_voice": bool(brand_voice),
        },
    }