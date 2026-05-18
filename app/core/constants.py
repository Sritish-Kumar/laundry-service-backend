from enum import Enum

class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"
    DELIVERY_AGENT = "DELIVERY_AGENT"
    ADMIN = "ADMIN"