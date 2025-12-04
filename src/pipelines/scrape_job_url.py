from loguru import logger
from playwright.sync_api import sync_playwright
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlencode
from apify_client import ApifyClient

# --- UPDATED: Selectors based *only* on the latest screenshots ---
SITE_SELECTORS = {
    "fr.indeed.com": {
        "job_title": "h1.jobsearch-JobInfoHeader-title",
        "company": "div[data-testid='jobsearch-CompanyInfoContainer']",
        "description_container": "#jobDescriptionText", 
    },
    # Add generic Indeed selectors as fallback
    "indeed.com": {
        "job_title": "h1.jobsearch-JobInfoHeader-title",
        "company": "div[data-testid='jobsearch-CompanyInfoContainer']",
        "description_container": "#jobDescriptionText",
    }
}

def run_apify_scraper(job_url: str) -> dict | None:
    """
    Uses the Apify 'misery/indeed-scraper' Actor to scrape the job.
    """
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        logger.warning("APIFY_API_TOKEN not found. Skipping Apify.")
        return None

    try:
        logger.info(f"Starting Apify Actor for {job_url}...")
        client = ApifyClient(api_token)
        
        # Prepare the Actor input
        run_input = {
            "startUrls": [{"url": job_url}],
            "maxItems": 1,
        }
        
        # Run the Actor and wait for it to finish
        # Actor: misery/indeed-scraper (h7sQ4K5p2) - Free/Cheap and reliable
        run = client.actor("h7sQ4K5p2").call(run_input=run_input)
        
        # Fetch results from the dataset
        logger.info(f"Actor run finished. Fetching results from dataset {run['defaultDatasetId']}...")
        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        
        if not dataset_items:
            logger.warning("Apify Actor returned no items.")
            return None
            
        item = dataset_items[0]
        
        # Map Apify output to our format
        # Note: The 'misery/indeed-scraper' output schema might vary, so we use .get() safely
        job_title = item.get("positionName") or item.get("jobTitle") or "Unknown Job Title"
        company = item.get("company") or "Unknown Company"
        # Some actors return 'description' or 'jobDescription'
        job_desc = item.get("description") or item.get("jobDescription") or ""
        
        # --- VALIDATION ---
        if job_title == "Unknown Job Title":
             logger.warning("Apify: Job title missing. Marking as failed.")
             return None

        if not job_desc or len(job_desc) < 50:
            logger.warning(f"Apify: Job description missing or too short ({len(job_desc)} chars). Marking as failed.")
            return None

        logger.success(f"Apify Success: {job_title} at {company}")
        
        return {
            "job_title": job_title,
            "company": company,
            "job_desc": job_desc,
            "job_url": job_url,
        }

    except Exception as e:
        logger.error(f"Apify scraper failed: {e}")
        return None

def _extract_from_html(html_content: str, job_url: str) -> dict | None:
    """
    Parses raw HTML (from fallback) to extract job details.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    hostname = urlparse(job_url).hostname
    
    # Normalize hostname for selector lookup
    selectors = SITE_SELECTORS.get(hostname)
    if not selectors:
        # Try to find a matching key (e.g., 'indeed.com' for 'fr.indeed.com')
        for site, sel in SITE_SELECTORS.items():
            if site in hostname:
                selectors = sel
                break
    
    if not selectors:
        logger.warning(f"No specific selectors found for {hostname}, trying generic fallback.")
        # Generic fallback (could be improved)
        selectors = SITE_SELECTORS["indeed.com"]

    try:
        # 1. Job Title
        title_tag = soup.select_one(selectors["job_title"])
        job_title = title_tag.get_text(strip=True) if title_tag else "Unknown Job Title"
        
        # 2. Company
        company_tag = soup.select_one(selectors["company"])
        company = company_tag.get_text(strip=True) if company_tag else "Unknown Company"
        
        # 3. Description
        desc_tag = soup.select_one(selectors["description_container"])
        if desc_tag:
            # Get text with newlines for readability
            job_desc = desc_tag.get_text(separator="\n", strip=True)
        else:
            job_desc = ""
            
        # --- VALIDATION ---
        if job_title == "Unknown Job Title":
             logger.warning("Job title could not be extracted. Likely a search page or blocked. Marking as failed.")
             return None

        if not job_desc or len(job_desc) < 50:
            logger.warning(f"Job description missing or too short ({len(job_desc)} chars). Marking as failed.")
            return None

        logger.info(f"Extracted: {job_title} at {company}")
        
        return {
            "job_title": job_title,
            "company": company,
            "job_desc": job_desc,
            "job_url": job_url,
        }

    except Exception as e:
        logger.error(f"Error parsing HTML content: {e}")
        return None


def run_url_scraper(job_url: str) -> dict | None:
    """
    Scrapes a job posting URL.
    Prioritizes Apify if configured, otherwise falls back to local Playwright.
    """
    logger.info(f"--- Starting Scraper Agent for URL: {job_url} ---")
    
    # 1. Try Apify
    if os.getenv("APIFY_API_TOKEN"):
        logger.info("APIFY_API_TOKEN found. Using Apify.")
        result = run_apify_scraper(job_url)
        if result:
            return result
        else:
            logger.warning("Apify failed. Falling back to local Playwright...")
    else:
        logger.info("No APIFY_API_TOKEN found. Using local Playwright.")

    # 2. Local Playwright Fallback
    try:
        hostname = urlparse(job_url).hostname
        
        if not hostname: 
            return None

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            logger.info(f"Navigating to {job_url} (Local)...")
            page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            
            # Basic Cloudflare check
            if "Just a moment" in page.title():
                logger.error("Cloudflare challenge detected locally. Apify is recommended.")
                browser.close()
                return None
                
            content = page.content()
            browser.close()
            
            return _extract_from_html(content, job_url)

    except Exception as e:
        logger.error(f"Local Playwright scraper failed: {e}")
        return None