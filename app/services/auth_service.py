from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.auth import (UserLoginRequest,
                              UserSignupRequest,
                              TokenResponse )
from app.repo.user_repo import UserRepository

from app.core.security  import (
    verify_password,
    hash_password,
    create_access_token
)

class AuthService:
    
    @staticmethod
    def signup(db: Session, signup_data: UserSignupRequest) -> TokenResponse:
        
        existing_user = UserRepository.get_user_by_email(db,signup_data.email)
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        user = User(
            full_name=signup_data.full_name,
            email=signup_data.email,
            phone=signup_data.phone,
            password_hash=hash_password(signup_data.password),
            role=signup_data.role
        )
        
        created_user = UserRepository.create_user(db, user)
        access_token = create_access_token(
            data={"sub": created_user.email, "role": created_user.role.value}
        )

        return TokenResponse(access_token=access_token)
    
    @staticmethod
    def login(db: Session, login_data: UserLoginRequest) -> TokenResponse:
        
        user = UserRepository.get_user_by_email(db, login_data.email)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        access_token = create_access_token(data={"sub": user.email, "role": user.role.value})
        
        return TokenResponse(access_token=access_token)        
