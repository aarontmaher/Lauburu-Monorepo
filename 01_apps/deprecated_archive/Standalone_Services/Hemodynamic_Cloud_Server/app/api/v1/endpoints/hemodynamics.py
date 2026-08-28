"""
Hemodynamic inversion endpoints: single-point inversion, batch processing, and live WebSocket stream.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from app.api.deps import get_inversion
from app.core.security import contains_pii, get_pii_violations
from app.models.schemas import (
    BatchInversionRequest,
    BatchInversionResponse,
    InversionRequest,
    ZeroPiiEdgeResponse,
)
from app.services.inversion_service import InversionService

router = APIRouter()


@router.post(
    "/invert",
    response_model=ZeroPiiEdgeResponse,
    status_code=status.HTTP_200_OK,
    summary="Invert 6D telemetry vector to hemodynamic blood pressure state"
)
async def invert_telemetry(
    request: InversionRequest,
    service: InversionService = Depends(get_inversion)
) -> ZeroPiiEdgeResponse:
    """
    Execute server-side non-linear Moens-Korteweg and Bramwell-Hill inversion
    from incoming anonymized Zero-PII vectors.
    """
    try:
        return await service.process_inversion(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hemodynamic inversion failed: {str(e)}"
        )


@router.post(
    "/batch",
    response_model=BatchInversionResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch inversion for buffered telemetry ticks"
)
async def batch_invert(
    request: BatchInversionRequest,
    service: InversionService = Depends(get_inversion)
) -> BatchInversionResponse:
    """Batch process buffered telemetry ticks with session aggregation."""
    try:
        return await service.process_batch(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch inversion failed: {str(e)}"
        )


@router.websocket("/stream")
async def websocket_telemetry_stream(
    websocket: WebSocket,
    service: InversionService = Depends(get_inversion)
):
    """
    Bidirectional WebSocket stream for real-time live telemetry ticks.
    Accepts InversionRequest JSON objects, yields ZeroPiiEdgeResponse JSON.
    """
    await websocket.accept()
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                if contains_pii(data):
                    violations = get_pii_violations(data)
                    await websocket.send_json({
                        "error": "Zero-PII Policy Violation",
                        "detail": violations[0] if violations else "Prohibited PII detected"
                    })
                    continue

                req = InversionRequest(**data)
                response = await service.process_inversion(req)
                await websocket.send_text(response.model_dump_json())
            except Exception as parse_err:
                await websocket.send_json({
                    "error": "Invalid telemetry payload",
                    "detail": str(parse_err)
                })
    except WebSocketDisconnect:
        pass
