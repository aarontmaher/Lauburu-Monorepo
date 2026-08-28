"""
Server-Sent Events (SSE) AI Diagnostic Streaming Endpoint.
Streams real-time diagnostic reasoning chunks separating <think> tokens and Markdown advice.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.security import validate_session_token_format
from app.models.schemas import DiagnosticStreamRequest
from app.services.genetic_moe_service import GeneticMoEService, get_genetic_moe_service

logger = logging.getLogger("AiStreamEndpoint")

router = APIRouter()


@router.post(
    "/diagnostic/stream",
    status_code=status.HTTP_200_OK,
    summary="Real-time Server-Sent Events (SSE) streaming diagnostic insights"
)
async def stream_diagnostic(
    request: DiagnosticStreamRequest,
    moe_service: GeneticMoEService = Depends(get_genetic_moe_service)
):
    """
    Streams incremental diagnostic reasoning chunks separating <think> tokens
    and Markdown coaching recommendations over text/event-stream with Zero-PII protection.
    """
    if not validate_session_token_format(request.session_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session token format (must be 64-character hex SHA-256 string)"
        )

    return StreamingResponse(
        moe_service.execute_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
