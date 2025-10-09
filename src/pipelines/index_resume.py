from __future__ import annotations
from pathlib import Path
from typing import List
from loguru import logger
from pypdf import PdfReader

from src.agents.memory import Memory

# --- Configuration ---
# You can adjust these later
CHUNK_SIZE = 800  # How many characters per chunk
CHUNK_OVERLAP = 100 # How much overlap between chunks

def _split_text_into_chunks(text: str) -> List[str]:
    """A simple text splitter. It's not perfect but a great start."""
    chunks = []
    for i in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP):
        chunk = text[i:i + CHUNK_SIZE]
        chunks.append(chunk)
    logger.info(f"Split text into {len(chunks)} chunks.")
    return chunks


def run_resume_indexer(pdf_path_str: str) -> None:
    """
    Reads a resume PDF, splits it into chunks, and stores them in a
    dedicated ChromaDB collection for semantic search.
    """
    pdf_path = Path(pdf_path_str)
    if not pdf_path.exists():
        logger.error(f"Resume PDF not found at: {pdf_path}")
        return

    # 1. Read the PDF content
    logger.info(f"Reading resume from {pdf_path}...")
    reader = PdfReader(pdf_path)
    resume_text = ""
    for page in reader.pages:
        resume_text += page.extract_text() or ""
    
    logger.success(f"Successfully extracted {len(resume_text)} characters from PDF.")

    # 2. Split text into chunks
    chunks = _split_text_into_chunks(resume_text)

    # 3. Store chunks in a new memory collection
    # We use a new collection to keep resume chunks separate from general profile info
    resume_memory = Memory("resume_chunks")
    
    # We need unique IDs for each chunk. A simple counter will do.
    doc_ids = [f"resume_chunk_{i}" for i in range(len(chunks))]

    resume_memory.col.add(
        ids=doc_ids,
        documents=chunks,
    )
    
    logger.success(f"Successfully indexed {len(chunks)} resume chunks into the 'resume_chunks' collection.")
    logger.info("First chunk preview: " + chunks[0][:200] + "...")


if __name__ == "__main__":
    # This allows us to run the script directly from the command line
    # Make sure your resume is in the project root or provide the correct path.
    run_resume_indexer("GabrielDalmoro_Resume_Software_2025.pdf")
