from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SYNC_SOURCE_URL: str = "http://176.57.188.243:1210/api/export/trips?format=jsonl"
    SYNC_INTERVAL_MINUTES: int = 60

    URL_FRONTEND: str = "http://localhost:3000"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Support"
    SMTP_USE_TLS: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()