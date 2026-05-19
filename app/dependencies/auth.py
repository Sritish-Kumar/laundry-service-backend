from jose import JWTError, jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.dependencies.database import get_db

from app.models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    
    # custom exception for invalid credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        
        if email is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    
    if user is None:
        raise credentials_exception
    
    return user
