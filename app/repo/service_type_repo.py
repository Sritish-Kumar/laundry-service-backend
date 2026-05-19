from sqlalchemy.orm import Session
from app.models.service_type import ServiceType

class ServiceTypeRepository:
    
    @staticmethod
    def create(db: Session,
               service_type: ServiceType) -> ServiceType:
        
        db.add(service_type)
        db.commit()
        db.refresh(service_type)
        
        return service_type
    
    
    @staticmethod
    def get_all(db:Session):
        return db.query(ServiceType).all()
    
    @staticmethod
    def get_by_id(db: Session,service_type_id):
        return db.query(ServiceType).filter(ServiceType.id==service_type_id).first()
    