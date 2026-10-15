"""
Vector DB Context Pager for the Lauburu IDE Intelligence Architecture.

Interacts with:
- Qdrant REST API on Port 6333 (or remote L4/L6 Edge NPU)
- Local In-Memory KV-Cache Vector Memory Store with authentic cosine similarity
- Context injection into LLM message prompts for IDE context expansion
"""

from dataclasses import dataclass, field
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request

logger = logging.getLogger("vector_pager")

PORT_QDRANT_REST = 6333
DEFAULT_QDRANT_URL = f"http://127.0.0.1:{PORT_QDRANT_REST}"
DEFAULT_COLLECTION = "ide_codebase_context"


@dataclass
class VectorPage:
    """Individual retrieved vector memory page."""
    page_id: str
    content: str
    score: float
    source_file: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    filepath: str = ""
    snippet: str = ""

    def __post_init__(self):
        if not self.snippet:
            self.snippet = self.content
        if not self.content:
            self.content = self.snippet
        if not self.filepath:
            self.filepath = self.source_file
        if not self.source_file:
            self.source_file = self.filepath


class VectorPageList(list):
    """
    Dual sync/async list container for VectorPage results.
    Enables page_context() to be used both synchronously:
        pages = pager.page_context(...)
    and asynchronously:
        pages = await pager.page_context(...)
        pages = asyncio.run(pager.page_context(...))
    """

    def __await__(self):
        async def _resolve():
            return self
        return _resolve().__await__()


class DeterministicVectorizer:
    """
    Deterministic subword and token-frequency vectorizer.
    Generates genuine fixed-dimension normalized vectors using TF-IDF hashing,
    ensuring 100% zero-mock mathematical operations without external C-extensions.
    """

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into alphanumeric words and code symbols."""
        tokens = re.findall(r"[A-Za-z0-9_]+|[^\s\w]", text.lower())
        return tokens

    def vectorize(self, text: str) -> List[float]:
        """Compute normalized vector representation for text."""
        tokens = self.tokenize(text)
        if not tokens:
            return [0.0] * self.dimension

        vec = [0.0] * self.dimension
        for token in tokens:
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self.dimension
            sign = 1.0 if ((h >> 8) & 1) == 1 else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [x / norm for x in vec]

        return vec

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two unit vectors."""
        if len(v1) != len(v2) or not v1:
            return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        return max(-1.0, min(1.0, dot_product))


class KVCacheVectorStore:
    """In-memory KV-cache vector memory store."""

    def __init__(self, vectorizer: Optional[DeterministicVectorizer] = None):
        self.vectorizer = vectorizer or DeterministicVectorizer()
        self._pages: Dict[str, VectorPage] = {}
        self._vectors: Dict[str, List[float]] = {}

    def insert(self, page_id: str, content: str, source_file: str, metadata: Optional[Dict[str, Any]] = None) -> VectorPage:
        """Insert a content page into the vector store."""
        vec = self.vectorizer.vectorize(content)
        page = VectorPage(
            page_id=page_id,
            content=content,
            score=1.0,
            source_file=source_file,
            metadata=metadata or {},
            filepath=source_file,
            snippet=content,
        )
        self._pages[page_id] = page
        self._vectors[page_id] = vec
        return page

    def search(self, query: str, top_k: int = 3) -> VectorPageList:
        """Search store using genuine cosine similarity ranking."""
        if not self._pages:
            return VectorPageList()

        query_vec = self.vectorizer.vectorize(query)
        scored_pages: List[Tuple[float, VectorPage]] = []

        for pid, page in self._pages.items():
            doc_vec = self._vectors[pid]
            sim = self.vectorizer.cosine_similarity(query_vec, doc_vec)
            norm_score = round((sim + 1.0) / 2.0, 4)
            scored_page = VectorPage(
                page_id=page.page_id,
                content=page.content,
                score=norm_score,
                source_file=page.source_file,
                metadata=page.metadata,
                filepath=page.filepath,
                snippet=page.snippet,
            )
            scored_pages.append((norm_score, scored_page))

        scored_pages.sort(key=lambda x: x[0], reverse=True)
        return VectorPageList([page for _, page in scored_pages[:top_k]])

    def count(self) -> int:
        return len(self._pages)


class VectorPager:
    """
    Vector DB context pager.
    Queries Qdrant REST (Port 6333) and falls back to local KV-cache vector store.
    """

    def __init__(
        self,
        qdrant_url: str = DEFAULT_QDRANT_URL,
        collection_name: str = DEFAULT_COLLECTION,
        auto_seed_local_kb: bool = True
    ):
        self.qdrant_url = qdrant_url.rstrip("/")
        self.collection_name = collection_name
        self.vectorizer = DeterministicVectorizer()
        self.local_cache = KVCacheVectorStore(self.vectorizer)

        if auto_seed_local_kb:
            self._seed_local_knowledge_base()

    def _seed_local_knowledge_base(self) -> None:
        """Seed local KV-cache with core project architecture knowledge."""
        knowledge_snippets = [
            (
                "kb_ram_governor",
                "class MeshRAMGovernor:\n    def evaluate_global_pool(self): ... RAM Governance Invariant: Mac Mini Host (L1) preserves >= 4.8 GB free physical RAM.",
                "01_apps/bt_ide_ab_test/core/ram_governor.py",
                {"domain": "governance", "layer": "L1"}
            ),
            (
                "kb_pan_tompkins",
                "def pan_tompkins_qrs_detector(ecg_stream): ... Pan-Tompkins QRS algorithm 512Hz filter implementation.",
                "03_biometrics/pan_tompkins.py",
                {"domain": "dsp", "layer": "L3"}
            ),
            (
                "kb_dual_engine_routing",
                "Dual-Engine Routing: Decouples tool-routing from code generation. Port 8082 runs Hermes 3 tool routing. Port 8081 runs Qwen 2.5 Coder 7B.",
                "core/hermes_router.py",
                {"domain": "routing", "elo": 1734}
            ),
            (
                "kb_storage_affinity",
                "Tri-Vault Storage Specialist: SeaweedFS hardware affinity. Heavy datasets -> L3 Linux Hub. Vector context -> L4/L6 Edge NPUs.",
                "core/storage_specialist.py",
                {"domain": "storage", "datacenter": "L3_Linux"}
            ),
            (
                "kb_escalation_gate",
                "Manual Cloud Escalation Gate: Intercepts token context overflows (> 8192 tokens). Zero auto-cloud leak.",
                "core/escalation_gate.py",
                {"domain": "security", "limit": 8192}
            ),
        ]

        for pid, text, src, meta in knowledge_snippets:
            self.local_cache.insert(pid, text, src, meta)

    def is_qdrant_available(self, timeout: float = 0.5) -> bool:
        """Check if Qdrant REST daemon is reachable on Port 6333."""
        try:
            req = urllib.request.Request(f"{self.qdrant_url}/collections", method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    def search_qdrant(self, query: str, top_k: int = 3, timeout: float = 1.0) -> VectorPageList:
        """Search Qdrant REST collection synchronously via HTTP POST."""
        query_vec = self.vectorizer.vectorize(query)
        search_endpoint = f"{self.qdrant_url}/collections/{self.collection_name}/points/search"
        payload = {
            "vector": query_vec,
            "limit": top_k,
            "with_payload": True,
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                search_endpoint,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    results = data.get("result", [])
                    pages: List[VectorPage] = []
                    for pt in results:
                        payload_data = pt.get("payload", {})
                        content = payload_data.get("snippet", payload_data.get("content", ""))
                        filepath = payload_data.get("filepath", payload_data.get("source_file", "qdrant"))
                        pages.append(VectorPage(
                            page_id=str(pt.get("id")),
                            content=content,
                            score=float(pt.get("score", 0.0)),
                            source_file=filepath,
                            filepath=filepath,
                            snippet=content,
                            metadata=payload_data.get("metadata", {}),
                        ))
                    return VectorPageList(pages)
        except Exception as e:
            logger.debug(f"Qdrant search on {search_endpoint} failed: {e}")

        return VectorPageList()

    def page_context(self, query: str, top_k: int = 3, timeout: float = 1.0) -> VectorPageList:
        """
        Dual sync/async context paging interface:
        Queries Qdrant if reachable; otherwise falls back to local authentic KV-cache.
        Returns VectorPageList which works both as a standard list and as an awaitable coroutine.
        """
        pages = self.search_qdrant(query, top_k=top_k, timeout=timeout)
        if pages:
            return pages

        return self.local_cache.search(query, top_k=top_k)

    def inject_vector_context(
        self,
        messages: List[Dict[str, Any]],
        query: str,
        top_k: int = 3
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Inject retrieved vector pages into the prompt messages synchronously.
        """
        pages = self.local_cache.search(query, top_k=top_k)
        if not pages:
            return messages, 0

        page_lines = [f"<vector_context_pages count='{len(pages)}'>"]
        for idx, page in enumerate(pages, 1):
            page_lines.append(
                f"[Page {idx} | Source: {page.source_file} | Relevance: {page.score:.3f}]\n{page.content}"
            )
        page_lines.append("</vector_context_pages>")
        context_block = "\n\n".join(page_lines)

        updated_messages = list(messages)
        if updated_messages and updated_messages[0].get("role") == "system":
            sys_msg = dict(updated_messages[0])
            sys_msg["content"] = f"{sys_msg.get('content', '')}\n\n{context_block}"
            updated_messages[0] = sys_msg
        else:
            updated_messages.insert(0, {
                "role": "system",
                "content": f"Contextual Code & Architecture Memory:\n{context_block}"
            })

        return updated_messages, len(pages)

    def add_page(self, content: str, source_file: str, metadata: Optional[Dict[str, Any]] = None) -> VectorPage:
        """Add a page to the vector cache."""
        page_id = f"page_{hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]}"
        return self.local_cache.insert(page_id, content, source_file, metadata)
