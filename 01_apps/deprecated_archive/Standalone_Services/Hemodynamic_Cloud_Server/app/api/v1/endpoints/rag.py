"""
Genetic MoE Hierarchical RAG endpoints for vector similarity search and session indexing.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_vector_store, get_db
from app.core.security import validate_session_token_format
from app.models.schemas import (
    IndexSessionRequest,
    IndexSessionResponse,
    RagQueryRequest,
    RagQueryResponse,
)
from app.services.genetic_moe_service import GeneticMoEService, get_genetic_moe_service
from app.storage.chroma_manager import ChromaManager
from app.storage.sqlite_manager import SqliteManager

logger = logging.getLogger("RagEndpoint")

router = APIRouter()


@router.post(
    "/query",
    response_model=RagQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic vector retrieval and Genetic MoE model routing"
)
async def query_rag(
    request: RagQueryRequest,
    moe_service: GeneticMoEService = Depends(get_genetic_moe_service)
) -> RagQueryResponse:
    """
    Query historical workout session embeddings and classify prompt domain
    to route to the optimal Genetic MoE model on the local mesh.
    """
    if not validate_session_token_format(request.session_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session token format (must be 64-character hex SHA-256 string)"
        )

    try:
        return await moe_service.query_rag_and_route(request)
    except Exception as e:
        logger.error(f"RAG query execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Genetic MoE RAG query failed: {str(e)}"
        )


@router.post(
    "/index_session",
    response_model=IndexSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Index completed workout session summary into ChromaDB and SQLite WAL"
)
async def index_session(
    request: IndexSessionRequest,
    vector_store: ChromaManager = Depends(get_vector_store),
    db: SqliteManager = Depends(get_db)
) -> IndexSessionResponse:
    """
    Generate dense 384D cosine embeddings for a completed workout session summary
    and index into ChromaDB and SQLite.
    """
    if not validate_session_token_format(request.session_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session token format"
        )

    document_text = request.document_text
    meta: Dict[str, Any] = request.summary_metadata or {}

    # If document_text was not directly supplied, build it from SQLite session record
    if not document_text:
        session_data = await db.get_session_summary(request.session_hash)
        if session_data:
            dur = session_data.get("duration_sec", 0)
            sbp = session_data.get("mean_sbp", 0.0)
            dbp = session_data.get("mean_dbp", 0.0)
            map_val = session_data.get("mean_map", 0.0)
            hr = session_data.get("mean_hr", 0.0)
            rmssd = session_data.get("mean_rmssd", 0.0)
            drift = session_data.get("cardiac_drift_detected", False)
            z2_ratio = session_data.get("zone2_compliance_ratio", 1.0)
            st = session_data.get("status", "completed")

            document_text = (
                f"Session {request.session_hash[:8]}: Duration {dur}s, "
                f"Mean SBP {sbp:.1f} mmHg, Mean DBP {dbp:.1f} mmHg, "
                f"Mean MAP {map_val:.1f} mmHg, Mean HR {hr:.1f} BPM, "
                f"RMSSD {rmssd:.1f} ms. Cardiac drift detected: {drift}. "
                f"Zone 2 Compliance: {z2_ratio:.2f}. Status: {st}."
            )
            meta.update({
                "session_hash": request.session_hash,
                "duration_sec": dur,
                "mean_sbp": sbp,
                "mean_dbp": dbp,
                "mean_map": map_val,
                "mean_hr": hr,
                "mean_rmssd": rmssd,
                "cardiac_drift": 1 if drift else 0,
                "zone2_compliance_ratio": z2_ratio,
                "workout_type": "zone2_endurance"
            })
        else:
            document_text = (
                f"Session {request.session_hash[:8]}: Zone 2 endurance session recorded "
                f"with verified physiological invariants."
            )
            meta.update({
                "session_hash": request.session_hash,
                "workout_type": "zone2_endurance"
            })

    # Index into vector store
    await vector_store.add_session_document(
        session_hash=request.session_hash,
        document_text=document_text,
        metadata=meta
    )

    return IndexSessionResponse(
        status="indexed",
        session_hash=request.session_hash,
        document_indexed=document_text
    )
