"""
Users API endpoints
"""

from fastapi import APIRouter, Depends

from app.core.database import get_session

router = APIRouter()


@router.get("/")
async def list_users():
    """List users - TODO"""
    return {"message": "Users endpoint - TODO"}
