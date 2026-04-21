from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "careerbridge"
    SECRET_KEY: str = "change-this-to-a-random-secret-key"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRY_HOURS: int = 24
    COOKIE_SECURE: bool = False
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ADMIN_EMAIL: str = "admin@careerbridge.com"
    ADMIN_PASSWORD: str = "admin123"

    class Config:
        env_file = ".env"


settings = Settings()
