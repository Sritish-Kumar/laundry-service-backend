from pydantic_settings import BaseSettings,SettingsConfigDict
import os

class Settings(BaseSettings):
    DATABASE_URL: str = ""
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env" if os.path.exists(".env") else None,
                                      extra="ignore",
                                      case_sensitive=True)
settings = Settings()

# The app will throw error on deployment if the .env 
# file is not found or if any of the required environment variables are missing. 
