"""
Session management endpoints for initializing anonymous workout sessions and fetching summaries.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_db, get_vector_store
from app.core.security import generate_session_token, validate_session_token_format
from app.models.schemas import SessionInitRequest, SessionInitResponse, SessionSummaryResponse
from app.storage.chroma_manager import ChromaManager
from app.storage.sqlite_manager import SqliteManager

router = APIRouter()


@router.post(
    "/init",
    response_model=SessionInitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize an anonymous Zero-PII session"
)
async def init_session(
    request: SessionInitRequest,
    db: SqliteManager = Depends(get_db)
) -> SessionInitResponse:
    """Generate an anonymous HMAC-SHA256 session token and initialize session in SQLite."""
    token = generate_session_token(nonce=request.client_nonce)
    now_ms = int(time.time() * 1000)
    await db.create_or_get_session(session_hash=token, created_at_epoch_ms=now_ms)
    return SessionInitResponse(
        session_token=token,
        status="initialized",
        created_at_epoch_ms=now_ms
    )


@router.get(
    "/{session_hash}/summary",
    response_model=SessionSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve summary metrics for a workout session"
)
async def get_session_summary(
    session_hash: str,
    db: SqliteManager = Depends(get_db),
    vector_store: ChromaManager = Depends(get_vector_store)
) -> SessionSummaryResponse:
    """Fetch session summary metrics. Automatically embeds summary into ChromaDB upon retrieval."""
    if not validate_session_token_format(session_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session token format (must be 64-char hex SHA-256 string)"
        )

    summary = await db.get_session_summary(session_hash)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with hash '{session_hash}' not found"
        )

    # Embed summary document into ChromaDB for future RAG queries
    doc_text = (
        f"Session {session_hash[:8]}: Duration {summary['duration_sec']}s, "
        f"Mean SBP {summary['mean_sbp']} mmHg, Mean DBP {summary['mean_dbp']} mmHg, "
        f"Mean MAP {summary['mean_map']} mmHg, Mean HR {summary['mean_hr']} BPM. "
        f"Cardiac drift detected: {summary['cardiac_drift_detected']}. "
        f"Status: {summary['status']}."
    )
    meta = {
        "session_hash": session_hash,
        "duration_sec": summary["duration_sec"],
        "mean_sbp": summary["mean_sbp"],
        "mean_dbp": summary["mean_dbp"],
        "mean_hr": summary["mean_hr"],
        "cardiac_drift": 1 if summary["cardiac_drift_detected"] else 0
    }
    await vector_store.add_session_document(
        session_hash=session_hash,
        document_text=doc_text,
        metadata=meta
    )

    return SessionSummaryResponse(**summary)
