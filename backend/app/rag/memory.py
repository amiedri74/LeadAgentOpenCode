import json
import os
import asyncio
import logging
import numpy as np
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

EMBED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "lead_embeddings.npy")
IDS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "lead_ids.json")
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768
CONCURRENCY = 10

_embedding_cache: Optional[dict] = None
_building = False


async def _ollama_embed_async(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "http://localhost:11434/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
        )
        r.raise_for_status()
        return r.json()["embedding"]


def lead_to_text(lead) -> str:
    parts = [
        lead.company_name or "",
        lead.contact_name or "",
        lead.email or "",
        lead.phone or "",
        lead.website or "",
        lead.address or "",
        lead.city or "",
        lead.zip_code or "",
        lead.service_category or "",
        lead.permit_type or "",
        lead.project_description or "",
    ]
    return " ".join(p for p in parts if p)


def load_index() -> dict:
    global _embedding_cache
    if _embedding_cache is not None:
        return _embedding_cache
    if not os.path.exists(EMBED_PATH) or not os.path.exists(IDS_PATH):
        _embedding_cache = {"embeddings": np.zeros((0, EMBED_DIM)), "ids": []}
        return _embedding_cache
    _embedding_cache = {
        "embeddings": np.load(EMBED_PATH),
        "ids": json.load(open(IDS_PATH)),
    }
    return _embedding_cache


def save_index(embeddings: np.ndarray, ids: list[str]):
    os.makedirs(os.path.dirname(EMBED_PATH), exist_ok=True)
    np.save(EMBED_PATH, embeddings)
    json.dump(ids, open(IDS_PATH, "w"))


async def build_index_async(db_leads: list, force: bool = False):
    global _embedding_cache, _building
    if _building:
        return None
    _building = True
    try:
        if not force and os.path.exists(EMBED_PATH):
            return load_index()

        texts = [lead_to_text(l) for l in db_leads]
        ids = [str(l.id) for l in db_leads]

        if not texts:
            idx = {"embeddings": np.zeros((0, EMBED_DIM)), "ids": ids}
            save_index(idx["embeddings"], idx["ids"])
            _embedding_cache = idx
            return idx

        logger.info("Building RAG index for %d leads...", len(texts))

        all_embeds = []
        for i in range(0, len(texts), CONCURRENCY):
            batch = texts[i:i + CONCURRENCY]
            results = await asyncio.gather(*[_ollama_embed_async(t) for t in batch], return_exceptions=True)
            for j, r in enumerate(results):
                if isinstance(r, Exception):
                    logger.warning("Embedding failed for lead %d: %s", i + j, r)
                    all_embeds.append([0.0] * EMBED_DIM)
                else:
                    all_embeds.append(r)
            if (i + CONCURRENCY) % 50 == 0 or (i + CONCURRENCY) >= len(texts):
                logger.info("Embedded %d/%d leads", min(i + CONCURRENCY, len(texts)), len(texts))

        idx = {"embeddings": np.array(all_embeds, dtype=np.float32), "ids": ids}
        save_index(idx["embeddings"], idx["ids"])
        _embedding_cache = idx
        logger.info("RAG index built: %d leads", len(ids))
        return idx
    finally:
        _building = False


def _embed_sync(text: str) -> np.ndarray:
    r = httpx.post(
        "http://localhost:11434/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=30,
    )
    r.raise_for_status()
    return np.array(r.json()["embedding"], dtype=np.float32)


def find_similar(query: str, n: int = 5, threshold: float = 0.5) -> list[dict]:
    idx = load_index()
    if len(idx["ids"]) == 0:
        return []

    q_vec = _embed_sync(query)

    dots = np.dot(idx["embeddings"], q_vec)
    norms = np.linalg.norm(idx["embeddings"], axis=1) * np.linalg.norm(q_vec)
    sims = np.divide(dots, norms, out=np.zeros_like(dots), where=norms != 0)

    top_n = min(n, len(sims))
    top_idx = np.argsort(sims)[-top_n:][::-1]

    results = []
    for i in top_idx:
        score = float(sims[i])
        if score < threshold:
            continue
        results.append({"lead_id": idx["ids"][i], "similarity": round(score, 4)})
    return results


def find_similar_to_lead(lead_id: str, n: int = 5, threshold: float = 0.5) -> list[dict]:
    idx = load_index()
    if lead_id not in idx["ids"]:
        return []

    pos = idx["ids"].index(lead_id)
    q_vec = idx["embeddings"][pos]

    dots = np.dot(idx["embeddings"], q_vec)
    norms = np.linalg.norm(idx["embeddings"], axis=1) * np.linalg.norm(q_vec)
    sims = np.divide(dots, norms, out=np.zeros_like(dots), where=norms != 0)
    sims[pos] = -1

    top_n = min(n, len(sims))
    top_idx = np.argsort(sims)[-top_n:][::-1]

    results = []
    for i in top_idx:
        score = float(sims[i])
        if score < threshold:
            continue
        results.append({"lead_id": idx["ids"][i], "similarity": round(score, 4)})
    return results
