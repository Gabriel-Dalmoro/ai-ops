from loguru import logger
from src.tools.notion_client import NotionTool

def run_job_tracker(
    job_title: str,
    company: str,
    job_url: str,
    status: str,  # <-- NEW PARAMETER
    fit_score: float,
    reason: str,
    cover_letter_text: str,
) -> str:
    """
    The Tracker Agent's main pipeline.
    Uses the NotionTool to create a comprehensive record in the Notion database.
    """
    logger.info(f"--- Starting Tracker Agent for: {job_title} ---")
    try:
        notion_tool = NotionTool()
        page_id = notion_tool.create_job_page(
            job_title=job_title,
            company=company,
            link=job_url,
            status=status,  # <-- USE THE PARAMETER
            fit_score=fit_score,
            reason=reason,
        )

        if page_id and cover_letter_text != "N/A - Job fit score was too low.":
            notion_tool.add_cover_letter_to_page(
                page_id=page_id,
                cover_letter_text=cover_letter_text,
            )
        
        logger.success(f"Tracker Agent finished. Job '{job_title}' logged to Notion with status '{status}'.")
        return page_id

    except Exception as e:
        logger.error(f"An error occurred in the Tracker Agent pipeline: {e}")
        return None
    