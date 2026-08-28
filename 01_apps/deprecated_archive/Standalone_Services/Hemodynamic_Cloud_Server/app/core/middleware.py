"""
Zero-PII Sanitization Middleware enforcing strict PII rejection on all requests.
"""

import json
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from app.core.security import is_pii_key, is_pii_value, get_pii_violations


class ZeroPiiSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that intercepts incoming HTTP requests to strictly reject
    any payload, query parameter, or header containing Personally Identifiable Information (PII).
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Inspect Query Parameters
        for key, value in request.query_params.items():
            if is_pii_key(key):
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": f"Zero-PII Policy Violation: Prohibited query parameter '{key}'",
                        "violation_type": "prohibited_query_param"
                    }
                )
            if is_pii_value(value):
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": f"Zero-PII Policy Violation: Prohibited value in query parameter '{key}'",
                        "violation_type": "prohibited_value_pattern"
                    }
                )

        # 2. Inspect Headers for Custom PII Keys
        for header_name, header_value in request.headers.items():
            h_lower = header_name.lower()
            if h_lower.startswith("x-"):
                clean_name = h_lower[2:].replace("-", "_")
                if is_pii_key(clean_name):
                    return JSONResponse(
                        status_code=422,
                        content={
                            "detail": f"Zero-PII Policy Violation: Prohibited header '{header_name}'",
                            "violation_type": "prohibited_header"
                        }
                    )

        # 3. Inspect JSON Body for Mutations
        if request.method in ("POST", "PUT", "PATCH"):
            body_bytes = await request.body()
            if body_bytes:
                # Check if body is JSON
                try:
                    payload = json.loads(body_bytes.decode("utf-8"))
                    violations = get_pii_violations(payload)
                    if violations:
                        return JSONResponse(
                            status_code=422,
                            content={
                                "detail": f"Zero-PII Policy Violation: Request payload contains prohibited PII ({violations[0]})",
                                "violations": violations,
                                "violation_type": "prohibited_payload_body"
                            }
                        )
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Non-JSON payloads will be validated by downstream route handlers
                    pass

        # Proceed to next middleware/handler
        return await call_next(request)
