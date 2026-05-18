from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.auth import (
    UserSignupRequest,
    UserLoginRequest,
    TokenResponse
)
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=TokenResponse)
def signup(signup_data: UserSignupRequest, db: Session = Depends(get_db)):
    
    return AuthService.signup(db,signup_data)

@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLoginRequest, db: Session = Depends(get_db)):
    
    return AuthService.login(db,login_data)