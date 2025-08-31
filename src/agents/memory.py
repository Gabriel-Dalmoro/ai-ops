from typing import Any, Dict, List, Tuple
from chromadb import Client
from chromadb.config import Settings

class Memory:
    """Light wrapper around ChromaDB for semantic memory.

    Collections we will use short-term:
    - profile: stores user's resume, brand voice, links, etc.
    - jobs: normalized job postings we ingest.
    """

    def __init__(self, collection: str = "profile") -> None:
        self.client = Client(Settings(anonymized_telemetry=False))
        self.col = self.client.get_or_create_collection(collection)

    def upsert(self, doc_id: str, text: str, metadata: Dict[str, Any] | None = None) -> None:
        self.col.upsert(ids=[doc_id], documents=[text], metadatas=[metadata or {}])

    def get(self, doc_id: str) -> str | None:
        # Chroma doesn't have direct get-by-id in the client API; emulate via where clause
        res = self.col.get(ids=[doc_id])
        docs = res.get("documents", [])
        return docs[0] if docs else None

    def similar(self, query: str, k: int = 4) -> List[Tuple[str, Dict[str, Any]]]:
        res = self.col.query(query_texts=[query], n_results=k)
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        return list(zip(docs, metas))
