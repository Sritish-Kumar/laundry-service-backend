from pydantic_settings import BaseSettings,SettingsConfigDict
import os

class Settings(BaseSettings):
    DATABASE_URL: str = ""
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    OTP_LENGTH: int = 6
    OTP_EXPIRY_MINUTES: int = 10
    OTP_MAX_FAILED_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True
    
    EMAIL_PROVIDER: str = "resend"
    RESEND_API_KEY: str | None = None
    EMAIL_FROM: str = "noreply@mail.laundry.sritishkumar.online"

    model_config = SettingsConfigDict(env_file=".env" if os.path.exists(".env") else None,
                                      extra="ignore",
                                      case_sensitive=True)
settings = Settings()

# The app will throw error on deployment if the .env 
# file is not found or if any of the required environment variables are missing. 
