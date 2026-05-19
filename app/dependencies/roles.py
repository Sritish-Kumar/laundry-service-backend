from fastapi import Depends

from app.dependencies.auth import get_current_user
from app.exceptions.custom_exceptions import PermissionDeniedError
from app.core.constants import UserRole

def require_roles(allowed_roles: list[UserRole]):
    
    def role_checker(current_user = Depends(get_current_user)):
        
        if current_user.role not in allowed_roles:
            raise PermissionDeniedError("Insufficient Permission")
        
        return current_user
    
    return role_checker