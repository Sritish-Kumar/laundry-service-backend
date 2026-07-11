from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.auth import TokenResponse, UserLoginRequest, UserSignupRequest
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=ApiResponse[TokenResponse])
def signup(signup_data: UserSignupRequest, db: Session = Depends(get_db)):
    """SignUp Route"""
    token = AuthService.signup(db, signup_data)

    return ApiResponse(
        success=True,
        message="User Created Successfully",
        data=token,
    )


@router.post("/login", response_model=ApiResponse[TokenResponse])
def login(login_data: UserLoginRequest, db: Session = Depends(get_db)):
    """Login Route"""
    token = AuthService.login(db, login_data)
    return ApiResponse(success=True, message="Login successful", data=token)


@router.post("/token", response_model=ApiResponse[TokenResponse])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 compatible token endpoint for Swagger UI authorization"""
    login_data = UserLoginRequest(email=form_data.username, password=form_data.password)
    token = AuthService.login(db, login_data)
    return ApiResponse(success=True, message="Login successful", data=token)