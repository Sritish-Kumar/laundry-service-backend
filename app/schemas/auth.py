from pydantic import BaseModel, EmailStr
from app.core.constants import UserRole

class UserSignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str
    role: UserRole
    

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str
    
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"