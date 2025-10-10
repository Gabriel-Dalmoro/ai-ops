from loguru import logger
import trafilatura
from bs4 import BeautifulSoup
import re

def run_url_scraper(job_url: str) -> dict | None:
    """
    Scrapes a job posting URL to extract the title, company, and description.
    Uses a generalist approach with trafilatura and BeautifulSoup.
    """
    logger.info(f"--- Starting Scraper Agent for URL: {job_url} ---")
    
    # Download the webpage's content
    downloaded = trafilatura.fetch_url(job_url)
    if not downloaded:
        logger.error("Failed to download the webpage.")
        return None

    # 1. Use BeautifulSoup to get a clean title
    soup = BeautifulSoup(downloaded, "html.parser")
    title = soup.find("title").get_text() if soup.find("title") else "No Title Found"
    
    # A simple regex to try and separate Company from Job Title (imperfect but a good start)
    # e.g., "Full-Stack Developer - Alpine Tech | LinkedIn" -> "Full-Stack Developer - Alpine Tech"
    title = title.split('|')[0].split(' at ')[0].strip()
    
    # Attempt to split title into job_title and company
    company = "Unknown Company"
    job_title = title
    if ' - ' in title:
        parts = title.rsplit(' - ', 1)
        job_title = parts[0]
        company = parts[1]

    logger.info(f"Extracted initial title: '{title}'")
    logger.info(f"Parsed as Job Title: '{job_title}', Company: '{company}'")

    # 2. Use trafilatura to get the main job description
    job_desc = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=False,
        no_fallback=True, # We want to fail if no main content is found
    )

    if not job_desc:
        logger.error("Trafilatura failed to extract main content from the page.")
        return None
        
    logger.success("Successfully extracted main content.")

    return {
        "job_title": job_title,
        "company": company,
        "job_desc": job_desc,
        "job_url": job_url,
    }