import os
import secrets
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME = os.getenv("APP_NAME", "Mango Talk API")
    APP_ENV = os.getenv("APP_ENV", "development")
    APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_DB = os.getenv("MYSQL_DB", "mango_talk")
    MYSQL_USER = os.getenv("MYSQL_USER", "mango_user")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
    UPLOAD_ROOT = os.getenv("UPLOAD_ROOT", os.path.join(PROJECT_ROOT, "uploads"))
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(50 * 1024 * 1024)))
    CORS_ORIGINS = [item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if item.strip()]

    def __init__(self):
        if self.APP_ENV == "production" and len(self.JWT_SECRET_KEY) < 32:
            raise ValueError("Production JWT_SECRET_KEY must contain at least 32 characters")
        if not self.JWT_SECRET_KEY:
            self.JWT_SECRET_KEY = secrets.token_urlsafe(48)

    @property
    def DATABASE_URL(self) -> str:
        return os.getenv("DATABASE_URL") or (
            f"mysql+pymysql://{quote_plus(self.MYSQL_USER)}:{quote_plus(self.MYSQL_PASSWORD)}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )


settings = Settings()
