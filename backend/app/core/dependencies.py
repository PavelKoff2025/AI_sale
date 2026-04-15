from fastapi import Depends, Header, HTTPException

from app.core.config import Settings, settings


def get_settings() -> Settings:
    return settings


async def verify_admin_key(x_admin_key: str = Header(default="")) -> str:
    if not settings.admin_api_key:
        return "no-auth"
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key header")
    return x_admin_key
