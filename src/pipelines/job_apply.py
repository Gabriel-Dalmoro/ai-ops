from pathlib import Path
from typing import Optional
from loguru import logger
from src.agents.memory import Memory


def run_job_apply_stub(job_title: str, job_desc: str, resume_text: Optional[str] = None, brand_voice: Optional[str] = None) -> dict:
    """
    Stub pipeline that:
    - Loads resume/brand_voice from memory if not provided.
    - Writes a fake cover letter & resume bullets to /out/{job_title}
    """
    profile = Memory("profile")

    # Resolve resume text
    if not resume_text:
        resume_text = profile.get("resume") or "[No resume on file yet]"

    # Resolve brand voice
    if not brand_voice:
        brand_voice = profile.get("brand_voice") or "Concise, optimistic, systems-builder tone."

    out_dir = Path("out") / job_title.replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Fake cover letter uses job + brand voice + tiny slice of resume
    resume_snippet = (resume_text[:300] + "…") if len(resume_text or "") > 300 else (resume_text or "")
    cover_letter = (
        f"Dear Hiring Manager,\n\n"
        f"I'm excited about the {job_title} role. My experience includes: {resume_snippet}\n\n"
        f"Tone: {brand_voice}\n\n"
        f"Best,\nGabriel"
    )
    cover_path = out_dir / "cover_letter.md"
    cover_path.write_text(cover_letter, encoding="utf-8")

    bullets = [
        "- Built AI-driven automations and pipelines.",
        "- Experienced with Next.js, TypeScript, and FastAPI.",
        "- Multilingual: English, Portuguese, Spanish; learning French.",
    ]
    bullets_path = out_dir / "resume_bullets.md"
    bullets_path.write_text("\n".join(bullets), encoding="utf-8")

    logger.info(f"Stub pipeline finished for {job_title}")

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
