from loguru import logger
from playwright.sync_api import sync_playwright
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlencode

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

class ScraperAPIClient:
    """
    A generic client for Scraper APIs (like ZenRows, ScraperAPI, ScrapingAnt).
    Most of these APIs work by sending the target URL as a parameter to their endpoint.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Default to a generic proxy-style API structure (compatible with ScraperAPI/ZenRows via params)
        # Users can override this if they have a specific provider preference in the future
        self.api_url = "https://api.scraperapi.com" 
        # Note: ZenRows uses 'https://api.zenrows.com/v1/'
        # We will try to detect or default to ScraperAPI for now as it's a common standard,
        # but this logic can be easily swapped.
        
        # If the key looks like a ZenRows key (usually starts with specific chars or user config), we could switch.
        # For now, we'll assume the user might set SCRAPER_API_URL if they use a different provider.
        self.api_endpoint = os.getenv("SCRAPER_API_URL", "https://api.scraperapi.com")

    def scrape(self, target_url: str) -> str | None:
        """
        Fetches the HTML of the target URL using the scraping API.
        """
        params = {
            "api_key": self.api_key,
            "url": target_url,
            "render": "true", # Request JS rendering
            "premium": "true", # Required for Indeed on ScraperAPI
            "country_code": "fr", # Helpful for fr.indeed.com
        }
        
        # ZenRows specific params adjustment if detected (naive check)
        if "zenrows" in self.api_endpoint:
             params = {
                "apikey": self.api_key,
                "url": target_url,
                "js_render": "true",
                "premium_proxy": "true",
                "location": "fr",
            }

        try:
            logger.info(f"Calling Scraper API ({self.api_endpoint}) for {target_url}...")
            response = requests.get(self.api_endpoint, params=params, timeout=60)
            
            if response.status_code == 200:
                logger.success("Scraper API request successful.")
                return response.text
            elif response.status_code == 403:
                logger.error("Scraper API Key invalid or quota exceeded.")
            else:
                logger.error(f"Scraper API failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Error calling Scraper API: {e}")
            
        return None

def _extract_from_html(html_content: str, job_url: str) -> dict | None:
    """
    Parses raw HTML (from API or fallback) to extract job details.
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
            job_desc = "Description not found."
            
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
    Prioritizes Scraper API if configured, otherwise falls back to local Playwright.
    """
    logger.info(f"--- Starting Scraper Agent for URL: {job_url} ---")
    
    # 1. Try Scraper API
    api_key = os.getenv("SCRAPER_API_KEY")
    if api_key:
        logger.info("SCRAPER_API_KEY found. Using Scraper API.")
        client = ScraperAPIClient(api_key)
        html_content = client.scrape(job_url)
        if html_content:
            return _extract_from_html(html_content, job_url)
        else:
            logger.warning("Scraper API failed. Falling back to local Playwright...")
    else:
        logger.info("No SCRAPER_API_KEY found. Using local Playwright.")

    # 2. Local Playwright Fallback
    try:
        hostname = urlparse(job_url).hostname
        # ... (Existing Playwright logic could go here, but for brevity and reliability, 
        # we might want to just return None if the API fails and we know local is blocked.
        # However, keeping a stripped down version is good for non-blocked sites.)
        
        if not hostname: 
            return None

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            logger.info(f"Navigating to {job_url} (Local)...")
            page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            
            # Basic Cloudflare check
            if "Just a moment" in page.title():
                logger.error("Cloudflare challenge detected locally. Scraper API is recommended.")
                browser.close()
                return None
                
            content = page.content()
            browser.close()
            
            return _extract_from_html(content, job_url)

    except Exception as e:
        logger.error(f"Local Playwright scraper failed: {e}")
        return None