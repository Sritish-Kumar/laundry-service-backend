from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
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
    """SignUp Route"""
    return AuthService.signup(db,signup_data)




@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLoginRequest, db: Session = Depends(get_db)):
    """Login Route"""
    return AuthService.login(db,login_data)




@router.post("/token", response_model=TokenResponse)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 compatible token endpoint for Swagger UI authorization"""
    # Convert form data to UserLoginRequest format
    login_data = UserLoginRequest(email=form_data.username, password=form_data.password)
    return AuthService.login(db, login_data)