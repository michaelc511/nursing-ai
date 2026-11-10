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


# ---------------------------------------------------------------- Phase 7: hybrid + re-rank (F18, F10)

RRF_K = 60


class CrossEncoderReranker:
    """F10: reads question and chunk together (more precise than vector distance)."""
    def __init__(self, model: str):
        from sentence_transformers import CrossEncoder
        self.name = model
        self._m = CrossEncoder(model)

    def score(self, query: str, texts: list[str]) -> list[float]:
        return [float(s) for s in self._m.predict([(query, t) for t in texts])]


_reranker = None
_reranker_set = False


def set_reranker(r) -> None:
    """Tests: set_reranker(None) turns re-ranking off."""
    global _reranker, _reranker_set
    _reranker, _reranker_set = r, True


def reranker():
    global _reranker, _reranker_set
    if not _reranker_set:
        _reranker = CrossEncoderReranker(settings.rerank_model) if settings.rerank else None
        _reranker_set = True
    return _reranker


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _candidates(col, cpt: str | None, queries: list[str]):
    """Every chunk in scope with its cosine score per query (policies are small: <= ~10 chunks each)."""
    where = {"cpt": cpt} if cpt else None
    n = len(col.get(where=where)["ids"]) if where else col.count()
    if n == 0:
        return {}, []
    per_query = []
    docs = {}
    for q in queries:
        res = col.query(query_embeddings=embedder().embed([q]), n_results=n, where=where)
        scores = {}
        for cid, doc, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]):
            docs[cid] = (doc, meta)
            scores[cid] = 1 - dist
        per_query.append(scores)
    return docs, per_query


def search(query: str, cpt: str | None = None, k: int = 4, extra_queries: list[str] | None = None) -> list[dict]:
    """Hybrid search: vector + BM25 per query, fused with Reciprocal Rank Fusion (also across the original and
    rewritten queries, S8), then cross-encoder re-ranking of the top 10. `score` stays the vector cosine of the
    best query (used for "I don't know" thresholds); `rerank` is the cross-encoder score."""
    col = collection()
    if col.count() == 0:
        return []
    queries = [query] + [q for q in (extra_queries or []) if q and q != query]
    docs, per_query = _candidates(col, cpt, queries)
    if not docs:
        return []
    ids = list(docs)
    bm25 = None
    if settings.hybrid:
        from rank_bm25 import BM25Okapi
        bm25 = BM25Okapi([_tokens(body_of(docs[i][0]) + " " + docs[i][1].get("section_title", "")) for i in ids])
    fused: dict[str, float] = {i: 0.0 for i in ids}
    for q, scores in zip(queries, per_query):
        for rank, cid in enumerate(sorted(ids, key=lambda i: -scores[i])):
            fused[cid] += 1 / (RRF_K + rank + 1)
        if bm25 is not None:
            bm = bm25.get_scores(_tokens(q))
            for rank, idx in enumerate(sorted(range(len(ids)), key=lambda j: -bm[j])):
                if bm[idx] > 0:
                    fused[ids[idx]] += 1 / (RRF_K + rank + 1)
    order = sorted(ids, key=lambda i: -fused[i])[:10]
    rr = reranker()
    rscores = {}
    if rr is not None and len(order) > 1:
        rscores = dict(zip(order, rr.score(query, [body_of(docs[i][0]) for i in order])))
        order = sorted(order, key=lambda i: -rscores[i])
    out = []
    for cid in order[:k]:
        doc, meta = docs[cid]
        out.append({"id": cid, "score": round(max(s[cid] for s in per_query), 3),
                    "rerank": round(rscores[cid], 3) if cid in rscores else None,
                    "fused": round(fused[cid], 4), "text": doc, "quote": body_of(doc),
                    "cpt": meta["cpt"], "policy_number": meta["policy_number"], "version": meta["version"],
                    "label": meta["label"], "section_title": meta["section_title"], "page": meta["page"]})
    return out


def chunks_for(cpt: str) -> list[Chunk]:
    """All chunks of one policy straight from the PDF (no index needed); used by the UI/tests."""
    p = policy_svc.get_policy(cpt)
    return chunk_policy(policy_svc.policy_path(cpt)[0], p)


# ---------------------------------------------------------------- AI Assist knowledge base (Phase 6)

GUIDE = "guide"
GUIDE_PDF_NAME = "guide_me.pdf"


def guide_collection():
    collection()                                   # make sure the client exists
    return _client.get_or_create_collection(GUIDE, metadata={"hnsw:space": "cosine"}, embedding_function=None)


def guide_chunks(path) -> list[Chunk]:
    """guide_me.pdf -> one chunk per numbered section (recursive split if long), header = section title."""
    import re as _re
    from app.rag.chunker import _split_long, load_pages
    sections, cur = [], None
    for page_no, lines in load_pages(path):
        for ln in lines:
            s = ln.strip()
            if _re.match(r"^(NurseOps Now · AI Assist knowledge base|Page \d+$)", s):
                continue
            m = _re.match(r"^(\d+)\.\s+(.+)$", s)
            if m and len(s) < 80:
                cur = {"n": m.group(1), "title": m.group(2), "page": page_no, "lines": []}
                sections.append(cur)
            elif cur is not None:
                cur["lines"].append(s)
    out = []
    for sec in sections:
        for i, piece in enumerate(_split_long("\n".join(sec["lines"]))):
            cid = f"guide-{sec['n']}" + (f"-{i}" if i else "")
            out.append(Chunk(id=cid, text=f"[AI Assist guide | §{sec['n']} {sec['title']} | page {sec['page']}]\n{piece}",
                             meta={"section": sec["n"], "section_title": sec["title"], "page": sec["page"],
                                   "label": f"§{sec['n']}"}))
    return out


def index_guide() -> int:
    from app.config import BACKEND
    chunks = guide_chunks(BACKEND / "knowledge" / GUIDE_PDF_NAME)
    col = guide_collection()
    old = col.get()["ids"]
    if old:
        col.delete(ids=old)
    col.add(ids=[c.id for c in chunks], documents=[c.text for c in chunks], metadatas=[c.meta for c in chunks],
            embeddings=embedder().embed([c.text for c in chunks]))
    return len(chunks)


def search_guide(query: str, k: int = 3) -> list[dict]:
    col = guide_collection()
    if col.count() == 0:
        index_guide()
    res = col.query(query_embeddings=embedder().embed([query]), n_results=min(k, col.count()))
    return [{"id": i, "score": round(1 - d, 3), "label": m["label"], "section_title": m["section_title"],
             "page": m["page"], "quote": body_of(doc)}
            for i, doc, m, d in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])]
