from loguru import logger
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# --- UPDATED: Selector Configuration Based on Screenshots ---
SITE_SELECTORS = {
    "fr.indeed.com": { # Assuming French Indeed based on screenshots
        "job_title": "h1.jobsearch-JobInfoHeader-title",
        "company": "div[data-testid='jobsearch-CompanyInfoContainer']",
        "description_container": "#jobDescriptionText",
    },
    # Add other Indeed domains if needed (e.g., "www.indeed.com")
    # "www.indeed.com": { ... } 
    
    # --- Commenting out non-functional LinkedIn selectors ---
    # "www.linkedin.com": {
    #     "job_title": '[class*="job-details-jobs-unified-top-card__job-title"]', # Non-functional
    #     "company": '[class*="job-details-jobs-unified-top-card__primary-description-container"]', # Non-functional
    #     "description_container": "#job-details", # Non-functional
    # },
}

def run_url_scraper(job_url: str) -> dict | None:
    """
    Scrapes a job posting URL using Playwright with stealth settings.
    Uses site-specific selectors based on inspected HTML. Includes Cloudflare mitigation.
    """
    logger.info(f"--- Starting STEALTH Scraper Agent for URL: {job_url} ---")
    
    try:
        hostname = urlparse(job_url).hostname
        if not hostname or hostname not in SITE_SELECTORS:
            logger.error(f"Scraper not configured for hostname: {hostname}. Check SITE_SELECTORS.")
            return None
        
        selectors = SITE_SELECTORS[hostname]
        logger.info(f"Using scraper configuration for: {hostname}")

    except Exception as e:
        logger.error(f"URL parsing/Selector lookup error: {e}")
        return None

    with sync_playwright() as p:
        browser = None # Define browser outside try block for closing in finally
        try:
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context()
            
            # --- Apply Stealth ---
            stealth(context)
            logger.info("Applied stealth settings to browser context.")
            
            page = context.new_page()
            
            logger.info(f"Navigating to {job_url}...")
            # Increased timeout and wait_until might help with Cloudflare
            page.goto(job_url, wait_until="networkidle", timeout=60000) 
            logger.info("Page loaded. Checking for Cloudflare (basic check)...")

            # Basic Cloudflare check (might need more advanced checks later)
            if page.title() == "Just a moment...":
                logger.warning("Cloudflare challenge detected. Waiting might help...")
                # Playwright might handle simple challenges automatically with stealth
                # Wait for navigation or a known element after challenge
                page.wait_for_load_state("networkidle", timeout=30000) 
                if page.title() == "Just a moment...":
                     logger.error("Cloudflare challenge persistent. Scraping likely failed.")
                     raise Exception("Cloudflare challenge blocked access.")
                else:
                    logger.info("Potentially bypassed Cloudflare challenge.")

            # --- Use ACTUAL Indeed Selectors ---
            description_selector = selectors["description_container"]
            logger.info(f"Waiting for description selector: '{description_selector}'")
            page.wait_for_selector(description_selector, timeout=20000) 
            logger.info("Description container found.")

            job_title = page.locator(selectors["job_title"]).inner_text(timeout=5000)
            logger.info(f"Extracted Job Title: '{job_title}'")
            
            company_info_locator = page.locator(selectors["company"])
            # Extract text carefully, handling potential sub-elements
            company_name = company_info_locator.locator('div[data-testid="jobsearch-CompanyReview--heading"]').inner_text(timeout=5000)
            # Add more specific locators if needed based on structure inside company container
            logger.info(f"Extracted Company Name: '{company_name}'")

            job_desc_html = page.locator(description_selector).inner_html(timeout=5000)
            logger.info("Extracted description HTML.")
            
            soup = BeautifulSoup(job_desc_html, "html.parser")
            job_desc_text = soup.get_text(separator="\n", strip=True)
            logger.info(f"Extracted description text (length: {len(job_desc_text)}). Preview: '{job_desc_text[:100]}...'")

            logger.success(f"Successfully extracted job: '{job_title}' at '{company_name}'")
            
            return {
                "job_title": job_title,
                "company": company_name,
                "job_desc": job_desc_text,
                "job_url": job_url,
            }

        except Exception as e:
            logger.error(f"Playwright operation failed for URL '{job_url}': {e}")
            return None
        finally:
             if browser:
                  browser.close()
                  logger.info("Browser closed.")

# from loguru import logger
# from playwright.sync_api import sync_playwright
# import os
# from bs4 import BeautifulSoup
# from urllib.parse import urlparse

# # --- NEW: Professional-grade Selector Configuration ---
# # This is our library of site-specific instructions.
# # Adding a new site is as easy as adding a new entry here.
# SITE_SELECTORS = {
#       "www.linkedin.com": {
#         "job_title": '[class*="job-details-jobs-unified-top-card__job-title"]',
#         "company": '[class*="job-details-jobs-unified-top-card__primary-description-container"]',
#         "description_container": "#job-details",
#     },
#     # EXAMPLE: How you would add another site in the future
#     # "ca.indeed.com": {
#     #     "job_title": ".jobsearch-JobInfoHeader-title",
#     #     "company": "[data-testid='jobsearch-CompanyInfoContainer']",
#     #     "description_container": "#jobDescriptionText",
#     # }
# }

# def run_url_scraper(job_url: str) -> dict | None:
#     """
#     Scrapes a job posting URL using a headless browser (Playwright).
#     It uses a configuration object to find the correct CSS selectors
#     for different job board websites, making it extensible.
#     """
#     logger.info(f"--- Starting Playwright Scraper Agent for URL: {job_url} ---")
    
#     li_at_cookie = os.getenv("LINKEDIN_LI_AT_COOKIE")
#     if not li_at_cookie:
#         logger.error("LINKEDIN_LI_AT_COOKIE not found. Cannot log in for scraping.")
#         return None

#     # --- NEW: Determine which site we're scraping ---
#     try:
#         hostname = urlparse(job_url).hostname
#         if not hostname or hostname not in SITE_SELECTORS:
#             logger.error(f"Scraper not configured for hostname: {hostname}. Aborting.")
#             return None
        
#         selectors = SITE_SELECTORS[hostname]
#         logger.info(f"Using scraper configuration for: {hostname}")

#     except Exception as e:
#         logger.error(f"Could not parse URL or find selectors: {e}")
#         return None

#     with sync_playwright() as p:
#         try:
#             browser = p.chromium.launch(headless=True)
#             context = browser.new_context()
            
#             # Add authentication cookie - essential for LinkedIn
#             context.add_cookies([{
#                 "name": "li_at", "value": li_at_cookie,
#                 "domain": ".linkedin.com", "path": "/"
#             }])

#             page = context.new_page()
#             page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
            
#             # Use the specific selector for the description to wait for the page to load
#             description_selector = selectors["description_container"]
#             page.wait_for_selector(description_selector, timeout=15000)

#             # --- UPDATED: Use selectors from our config object ---
#             job_title = page.locator(selectors["job_title"]).inner_text()
#             company_name = page.locator(selectors["company"]).inner_text()
#             job_desc_html = page.locator(description_selector).inner_html()
            
#             # Clean the HTML to plain text for the LLM
#             soup = BeautifulSoup(job_desc_html, "html.parser")
#             job_desc_text = soup.get_text(separator="\n").strip()

#             logger.success(f"Successfully extracted job: '{job_title}' at '{company_name}'")
#             browser.close()
            
#             return {
#                 "job_title": job_title,
#                 "company": company_name,
#                 "job_desc": job_desc_text,
#                 "job_url": job_url,
#             }

#         except Exception as e:
#             logger.error(f"Playwright failed to scrape the URL '{job_url}': {e}")
#             if 'browser' in locals():
#                 browser.close()
#             return None