from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.schemas.user import UserResponse
from app.models import User


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
    