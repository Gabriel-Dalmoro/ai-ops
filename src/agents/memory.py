from typing import Any, Dict, List, Tuple
import chromadb

class Memory:
    """
    Light wrapper around ChromaDB for semantic memory.
    This version uses a persistent client to save data to disk.
    """
    _client = chromadb.PersistentClient(path="./chroma_db")

    def __init__(self, collection: str = "profile") -> None:
        self.col = self._client.get_or_create_collection(collection)

    def upsert(self, doc_id: str, text: str, metadata: Dict[str, Any] | None = None) -> None:
        self.col.upsert(ids=[doc_id], documents=[text], metadatas=[metadata or {}])

    def get(self, doc_id: str) -> str | None:
        res = self.col.get(ids=[doc_id])
        docs = res.get("documents", [])
        return docs[0] if docs else None

    def get_resume_fingerprint(self) -> str | None:
        return self.get("resume_fingerprint")

    def set_resume_fingerprint(self, fingerprint: str) -> None:
        self.upsert("resume_fingerprint", fingerprint, {"type": "fingerprint"})

    def similar(self, query: str, k: int = 4) -> List[Tuple[str, Dict[str, Any]]]:
        res = self.col.query(query_texts=[query], n_results=k)
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        return list(zip(docs, metas))

