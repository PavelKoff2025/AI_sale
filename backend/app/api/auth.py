from fastapi import APIRouter, Request

from app.core.jwt_auth import create_token

router = APIRouter()


@router.post("/token")
async def get_token(request: Request):
    """Issue a short-lived JWT for the chat widget.

    No credentials required — the token serves as a lightweight
    anti-abuse mechanism. Rate limiting on this endpoint prevents
    token farming.
    """
    client_ip = request.headers.get("X-Forwarded-For", "")
    if not client_ip and request.client:
        client_ip = request.client.host

    token, expires_in = create_token(
        subject="widget",
        extra={"ip": client_ip},
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }
