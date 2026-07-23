import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.dependencies.database import get_db
from app.exceptions.custom_exceptions import AuthenticationError
from app.models import User
from app.repo.user_repo import UserRepository


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    
    # custom exception for invalid credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception

        parsed_user_id = uuid.UUID(user_id)
        
    except (AuthenticationError, ValueError):
        raise credentials_exception
    
    user = UserRepository.get_user_by_id(db, parsed_user_id)
    
    if user is None:
        raise credentials_exception
    
    return user


def get_current_session_id(token: str = Depends(oauth2_scheme)) -> uuid.UUID:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        session_id = payload.get("sid")
        if session_id is None:
            raise credentials_exception
        return uuid.UUID(str(session_id))
    except (AuthenticationError, ValueError):
        raise credentials_exception
