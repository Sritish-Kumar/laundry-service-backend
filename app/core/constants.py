from enum import Enum

class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"
    DELIVERY_AGENT = "DELIVERY_AGENT"
    ADMIN = "ADMIN"
    
class OrderStatus(str,Enum):
    PENDING_PICKUP = 'PENDING_PICKUP'
    PICKED_UP = 'PICKED_UP'
    RECEIVED = 'RECEIVED'
    
    SORTING = 'SORTING'
    WASHING = 'WASHING'
    DRYING = 'DRYING'
    IRONING = 'DRYING'
    PACKING = 'PACKING'
    
    OUT_FOR_DELIVERY= 'OUT_FOR_DELIVERY'
    DELIVERED='DELIVERED'
    
    CANCELLED='CANCELLED'

class DeviceType(str, Enum):
    WEB = 'WEB'
    MOBILE = 'MOBILE'
    TABLET = 'TABLET'
    DESKTOP = 'DESKTOP'
    