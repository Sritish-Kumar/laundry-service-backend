from pydantic import BaseModel, EmailStr,Field
from app.core.constants import UserRole

class UserSignupRequest(BaseModel):
    full_name: str =Field(min_length=2,max_length=50)
    email: EmailStr
    phone: str = Field(min_length=10,max_length=15)
    password: str = Field(min_length=8,max_length=128)
    role: UserRole
    
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str
    
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"