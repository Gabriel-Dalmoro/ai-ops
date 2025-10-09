import os
from notion_client import Client
from loguru import logger
from typing import List

class NotionTool:
    """
    A tool for interacting with a specific Notion database for job tracking.
    Handles creating and updating job application pages.
    """

    def __init__(self):
        self.api_key = os.getenv("NOTION_INTEGRATION_KEY")

        #TODO Add notion database ai
        self.database_id = os.getenv("NOTION_DATABASE_ID")

        if not self.api_key or not self.database_id:
            raise ValueError("NOTION_INTEGRATION_KEY and NOTION_DATABASE_ID must be set in.env")

        self.client = Client(auth=self.api_key)
        logger.info("NotionTool initialized and connected.")

    def create_job_page(
        self,
        job_title: str,
        company: str,
        link: str,
        status: str,
        fit_score: float,
        reason: str,
    ) -> str:
        """Creates a new page in the Notion database with the core properties."""
        properties = {
            "Job Title": {"title": [{"text": {"content": job_title}}]},
            "Company": {"rich_text": [{"text": {"content": company}}]},
            "Link": {"url": link},
            "Status": {"select": {"name": status}},
            "Fit Score": {"number": fit_score},
            "Reason": {"rich_text": [{"text": {"content": reason}}]},
        }

        try:
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
            )
            logger.success(f"Successfully created Notion page for '{job_title}'.")
            return response["id"]
        except Exception as e:
            logger.error(f"Failed to create Notion page: {e}")
            return None

    def add_cover_letter_to_page(self, page_id: str, cover_letter_text: str):
        """Appends the cover letter text to the body of a Notion page."""
        if not page_id:
            return

        # Split the cover letter into paragraphs for better formatting in Notion
        paragraphs = cover_letter_text.strip().split('\n\n')
        
        children_blocks: List[dict] = [
            # Add a heading first
            {
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Generated Cover Letter"}}]
                }
            }
        ]
        
        # Add each paragraph as a separate block
        for p in paragraphs:
            children_blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": p}}]
                }
            })

        try:
            self.client.blocks.children.append(block_id=page_id, children=children_blocks)
            logger.success(f"Successfully added cover letter to Notion page ID: {page_id}")
        except Exception as e:
            logger.error(f"Failed to add content to Notion page: {e}")

