from loguru import logger
from playwright.sync_api import sync_playwright
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse

#TODO Have to completely revamp and update the scrapper method and ideaa


def run_url_scraper(job_url: str) -> dict | None:
    """
    An advanced scraper using Playwright to handle dynamic, login-protected sites.
    It mimics human interaction by clicking "Show more" and uses robust selectors.
    """
    logger.info(f"--- Starting ADVANCED Scraper Agent for URL: {job_url} ---")
    
    li_at_cookie = os.getenv("LINKEDIN_LI_AT_COOKIE")
    if not li_at_cookie:
        logger.error("LINKEDIN_LI_AT_COOKIE not found. Cannot log in.")
        return None

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            context.add_cookies([{"name": "li_at", "value": li_at_cookie, "domain": ".linkedin.com", "path": "/"}])

            page = context.new_page()
            page.goto(job_url, wait_until="domcontentloaded", timeout=20000)

            # --- NEW: INTERACTIVE LOGIC ---
            
            # 1. Wait for the top card to be generally visible
            # This is a more stable landmark to wait for.
            top_card_selector = ".job-details-jobs-unified-top-card__content--two-pane"
            page.wait_for_selector(top_card_selector, timeout=15000)
            logger.info("Job top card is visible.")

            # 2. Click the "Show more" button to expand the description
            show_more_button_selector = ".jobs-description__footer-button"
            page.click(show_more_button_selector)
            logger.info("Clicked 'Show more' button to expand description.")

            # --- NEW: ROBUST SELECTOR LOGIC ---
            
            # Since classes are dynamic, we find elements by their role and position.
            # This finds the main h1, which is almost always the job title.
            job_title = page.locator(f"{top_card_selector} h1").inner_text()
            
            # This finds the container with company name, location, etc., and we take the first line.
            company_info_text = page.locator(f"{top_card_selector} .job-details-jobs-unified-top-card__primary-description-container").inner_text()
            company_name = company_info_text.split('·')[0].strip()

            # The main description container.
            description_container_selector = ".jobs-box__html-content"
            page.wait_for_selector(description_container_selector, timeout=5000)
            job_desc_html = page.locator(description_container_selector).inner_html()
            
            soup = BeautifulSoup(job_desc_html, "html.parser")
            job_desc_text = soup.get_text(separator="\n").strip()

            logger.success(f"Successfully extracted job: '{job_title}' at '{company_name}'")
            browser.close()
            
            return {
                "job_title": job_title,
                "company": company_name,
                "job_desc": job_desc_text,
                "job_url": job_url,
            }

        except Exception as e:
            logger.error(f"Playwright failed to scrape the URL '{job_url}': {e}")
            if 'browser' in locals():
                browser.close()
            return None

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