import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import UserRole

class UserResponse(BaseModel):
    
    id: uuid.UUID
    full_name: str
    email: str
    phone: str
    role: UserRole
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)