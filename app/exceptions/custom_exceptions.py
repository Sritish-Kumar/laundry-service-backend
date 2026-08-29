class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass

class NotFoundError(Exception):
    """Custom exception for not found errors."""
    pass

class ConflictError(Exception):
    """Custom exception for conflict errors."""
    pass

class PermissionDeniedError(Exception):
    """Custom exception for permission denied errors."""
    pass

class ValidationError(Exception):
    """Custom exception for validation errors (e.g. invalid Razorpay signature)."""
    pass