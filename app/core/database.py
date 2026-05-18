from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,DeclarativeBase

from app.core.config import settings

# Create the SQLAlchemy engine using the DATABASE_URL from settings
engine = create_engine(settings.DATABASE_URL,echo=True)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Parent orm base class for all models to inherit from
class Base(DeclarativeBase):
    pass
