"""Layer 3 RAG, step 4-5: embed (sentence-transformers, Claude never embeds) -> Chroma index -> search.

- One Chroma collection "policies"; every chunk carries S4 metadata (cpt, version, section, page).
- Search is filtered to ONE policy (CPT code -> policy), as CLAUDE.md Layer 3 says.
- Re-index a policy = delete its old chunks (all versions) and add the new ones.
- Chunks flagged as injection-like are kept out of the index (and reported).
Tests swap in a tiny offline embedder via set_embedder(); prod/demo use all-MiniLM-L6-v2.
"""
import hashlib
import math
import re
from typing import Protocol

from app.config import settings
from app.rag.chunker import Chunk, body_of, chunk_policy
from app.services import policy as policy_svc

COLLECTION = "policies"


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    def __init__(self, model: str):
        from sentence_transformers import SentenceTransformer  # heavy import: only when used
        self.name = model
        self._m = SentenceTransformer(model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._m.encode(texts, normalize_embeddings=True).tolist()


class HashEmbedder:
    """Offline bag-of-words embedder for tests (no model download, deterministic)."""
    name = "hash-test"

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for w in re.findall(r"[a-z0-9]+", t.lower()):
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % self.dim] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


_embedder: Embedder | None = None
_client = None


def set_embedder(e: Embedder | None) -> None:
    global _embedder
    _embedder = e


def embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformerEmbedder(settings.embed_model)
    return _embedder


def reset_client() -> None:
    global _client
    _client = None


def collection():
    global _client
    import chromadb
    if _client is None:
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    # Embeddings are always passed in, so Chroma's own default model is never used.
    return _client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"},
                                            embedding_function=None)


def index_policy(p: dict) -> dict:
    path, _ = policy_svc.policy_path(p["cpt"])
    chunks = chunk_policy(path, p)
    flagged = [c.id for c in chunks if c.meta["flagged"]]
    keep = [c for c in chunks if not c.meta["flagged"]]
    col = collection()
    col.delete(where={"cpt": p["cpt"]})          # old version(s) of this policy out
    if keep:
        col.add(ids=[c.id for c in keep], documents=[c.text for c in keep],
                metadatas=[c.meta for c in keep], embeddings=embedder().embed([c.text for c in keep]))
    return {"cpt": p["cpt"], "version": p["version"], "chunks": len(keep), "flagged": flagged}


def index_all() -> dict:
    results = [index_policy(p) for p in policy_svc.registry()]
    return {"embedder": embedder().name, "policies": results,
            "total_chunks": sum(r["chunks"] for r in results)}


def count() -> int:
    return collection().count()


def search(query: str, cpt: str | None = None, k: int = 4) -> list[dict]:
    """Top-k policy chunks. cpt narrows to that policy (the normal path); None = all policies."""
    col = collection()
    if col.count() == 0:
        return []
    res = col.query(query_embeddings=embedder().embed([query]), n_results=min(k, col.count()),
                    where={"cpt": cpt} if cpt else None)
    out = []
    for cid, doc, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0],
                                    res["distances"][0]):
        out.append({"id": cid, "score": round(1 - dist, 3), "text": doc, "quote": body_of(doc),
                    "cpt": meta["cpt"], "policy_number": meta["policy_number"], "version": meta["version"],
                    "label": meta["label"], "section_title": meta["section_title"], "page": meta["page"]})
    return out


def chunks_for(cpt: str) -> list[Chunk]:
    """All chunks of one policy straight from the PDF (no index needed); used by the UI/tests."""
    p = policy_svc.get_policy(cpt)
    return chunk_policy(policy_svc.policy_path(cpt)[0], p)
