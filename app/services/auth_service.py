from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.exceptions.custom_exceptions import AuthenticationError, ConflictError
from app.models import User
from app.repo.user_repo import UserRepository
from app.schemas.auth import TokenResponse, UserLoginRequest, UserSignupRequest


class AuthService:

    @staticmethod
    def signup(db: Session, signup_data: UserSignupRequest) -> TokenResponse:
        existing_user_by_email = UserRepository.get_user_by_email(db, signup_data.email)
        if existing_user_by_email:
            raise ConflictError("A user with this email already exists")

        existing_user_by_phone = UserRepository.get_user_by_phone(db, signup_data.phone)
        if existing_user_by_phone:
            raise ConflictError("A user with this phone number already exists")

        user = User(
            full_name=signup_data.full_name,
            email=signup_data.email,
            phone=signup_data.phone,
            password_hash=hash_password(signup_data.password),
            role=signup_data.role,
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
            raise AuthenticationError("Invalid email or password")

        if not verify_password(login_data.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        access_token = create_access_token(data={"sub": user.email, "role": user.role.value})

        return TokenResponse(access_token=access_token)