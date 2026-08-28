import asyncio
import hashlib
import json
import os
import re
import threading
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from app.core.config import settings

# Attempt to import chromadb, else provide exact fallback
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


def _compute_deterministic_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Generate a normalized deterministic pseudo-semantic vector embedding from text
    when external transformer models are not available.
    """
    words = re.findall(r"\w+", text.lower())
    vec = np.zeros(dim, dtype=np.float64)
    if not words:
        vec[0] = 1.0
        return vec.tolist()

    for idx, word in enumerate(words):
        h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
        slot = h % dim
        sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
        weight = 1.0 / (1.0 + 0.1 * idx)
        vec[slot] += sign * weight

    norm = np.linalg.norm(vec)
    if norm > 1e-9:
        vec = vec / norm
    else:
        vec[0] = 1.0
    return vec.tolist()


class FallbackVectorStore:
    """Local JSON/SQLite-backed deterministic vector store for zero-dependency environments."""

    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.store_file = os.path.join(storage_dir, "fallback_vectors.json")
        self._documents: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.store_file):
            try:
                with open(self.store_file, "r", encoding="utf-8") as f:
                    self._documents = json.load(f)
            except Exception:
                self._documents = []

    def _save(self) -> None:
        try:
            with open(self.store_file, "w", encoding="utf-8") as f:
                json.dump(self._documents, f, indent=2)
        except Exception:
            pass

    def add(
        self,
        doc_id: str,
        document: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        # Remove existing if any
        self._documents = [d for d in self._documents if d.get("id") != doc_id]
        self._documents.append({
            "id": doc_id,
            "document": document,
            "embedding": embedding,
            "metadata": metadata
        })
        self._save()

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 3,
        filter_session_hash: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self._documents:
            return []

        q_vec = np.asarray(query_embedding, dtype=np.float64)
        results = []
        for doc in self._documents:
            if filter_session_hash and doc.get("metadata", {}).get("session_hash") != filter_session_hash:
                continue
            d_vec = np.asarray(doc["embedding"], dtype=np.float64)
            # Cosine similarity
            denom = (np.linalg.norm(q_vec) * np.linalg.norm(d_vec))
            sim = float(np.dot(q_vec, d_vec) / denom) if denom > 1e-9 else 0.0
            results.append({
                "id": doc["id"],
                "document": doc["document"],
                "score": round(sim, 4),
                "metadata": doc["metadata"]
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


class ChromaManager:
    """Manages vector embeddings and semantic search for hemodynamic session summaries."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or settings.CHROMADB_DIR
        self._lock = threading.Lock()
        self.chroma_client = None
        self.collection = None
        self.fallback_store = None
        self._init_client()

    def _init_client(self) -> None:
        os.makedirs(self.persist_dir, exist_ok=True)
        if CHROMADB_AVAILABLE:
            try:
                self.chroma_client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=ChromaSettings(anonymized_telemetry=False)
                )
                self.collection = self.chroma_client.get_or_create_collection(
                    name="hemodynamic_workout_embeddings",
                    metadata={"hnsw:space": "cosine"}
                )
                return
            except Exception:
                pass

        # Use fallback vector store
        self.fallback_store = FallbackVectorStore(self.persist_dir)

    async def add_session_document(
        self,
        session_hash: str,
        document_text: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Add or update an anonymous session summary embedding."""
        embedding = _compute_deterministic_embedding(document_text)

        def _sync_add():
            with self._lock:
                if self.collection is not None:
                    try:
                        self.collection.upsert(
                            ids=[session_hash],
                            documents=[document_text],
                            embeddings=[embedding],
                            metadatas=[metadata]
                        )
                        return
                    except Exception:
                        pass
                if self.fallback_store is not None:
                    self.fallback_store.add(
                        doc_id=session_hash,
                        document=document_text,
                        embedding=embedding,
                        metadata=metadata
                    )

        await asyncio.to_thread(_sync_add)

    async def query_embeddings(
        self,
        query_text: str,
        top_k: int = 3,
        filter_session_hash: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic cosine distance vector search."""
        query_embedding = _compute_deterministic_embedding(query_text)

        def _sync_query() -> List[Dict[str, Any]]:
            with self._lock:
                if self.collection is not None:
                    try:
                        where_filter = {"session_hash": filter_session_hash} if filter_session_hash else None
                        res = self.collection.query(
                            query_embeddings=[query_embedding],
                            n_results=top_k,
                            where=where_filter
                        )
                        items = []
                        if res and res.get("documents") and len(res["documents"]) > 0:
                            docs = res["documents"][0]
                            metas = res["metadatas"][0] if res.get("metadatas") else [{}] * len(docs)
                            dists = res["distances"][0] if res.get("distances") else [0.0] * len(docs)
                            ids = res["ids"][0] if res.get("ids") else [""] * len(docs)
                            for doc, meta, dist, d_id in zip(docs, metas, dists, ids):
                                # Invert cosine distance to similarity score
                                score = round(1.0 - float(dist), 4) if dist is not None else 1.0
                                items.append({
                                    "id": d_id,
                                    "document": doc,
                                    "score": score,
                                    "metadata": meta or {}
                                })
                        return items
                    except Exception:
                        pass

                if self.fallback_store is not None:
                    return self.fallback_store.query(
                        query_embedding=query_embedding,
                        top_k=top_k,
                        filter_session_hash=filter_session_hash
                    )
                return []

        return await asyncio.to_thread(_sync_query)


def classify_genetic_moe_expert(query: str) -> Tuple[str, str]:
    """
    Classify query complexity and route to optimal local Genetic MoE model:
    - Deep cardiovascular reasoning / mathematical trend proofs -> DeepSeek-R1-Distill-Qwen-32B
    - Multi-modal biometrics / ECG graph inspections -> Qwen3-VL-32B
    - Fast workout summaries / tabular metrics -> Qwen2.5-Coder-14B
    - General hemodynamic query -> Qwen2.5-Coder-32B-Instruct
    """
    q_lower = query.lower()
    
    # 1. Multi-modal / ECG / Visual inspection
    if any(k in q_lower for k in ["ecg", "graph", "plot", "waveform", "chart", "visual", "morphology", "dicrotic"]):
        return (
            "Qwen3-VL-32B",
            "Multi-modal vision-language expert selected for biometrics waveform & ECG morphology inspection."
        )
        
    # 2. Deep cardiovascular reasoning / mathematical trend proofs
    if any(k in q_lower for k in ["proof", "stiffness", "derivation", "drift", "vascular", "why", "fatigue", "decay", "compliance"]):
        return (
            "DeepSeek-R1-Distill-Qwen-32B",
            "Deep reasoning model selected for mathematical trend proofs and cardiovascular hemodynamic analysis."
        )
        
    # 3. Tabular metrics / Fast workout summaries
    if any(k in q_lower for k in ["summary", "average", "stats", "tabular", "zone", "duration", "total"]):
        return (
            "Qwen2.5-Coder-14B",
            "Fast structured coding expert selected for workout summary aggregation and tabular metrics."
        )
        
    # 4. Default fallback
    return (
        "Qwen2.5-Coder-32B-Instruct",
        "Primary unified orchestrator model selected for comprehensive exercise physiology query response."
    )


_global_chroma_manager: Optional[ChromaManager] = None


def get_chroma_manager(persist_dir: Optional[str] = None) -> ChromaManager:
    global _global_chroma_manager
    if _global_chroma_manager is None or persist_dir is not None:
        _global_chroma_manager = ChromaManager(persist_dir)
    return _global_chroma_manager
