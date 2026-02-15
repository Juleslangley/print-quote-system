from pathlib import Path

from pydantic_settings import BaseSettings

# Load .env from project root; .env.local overrides for local dev (e.g. DATABASE_URL with localhost)
# __file__ is backend/app/core/config.py -> parent^3 = backend, parent^4 = repo root
_root_dir = Path(__file__).resolve().parent.parent.parent.parent
_env_files: list[Path] = []
if (_root_dir / ".env").exists():
    _env_files.append(_root_dir / ".env")
if (_root_dir / ".env.local").exists():
    _env_files.append(_root_dir / ".env.local")
if not _env_files:
    _env_files = [Path(".env")]

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str = "dev"
    PRICING_VERSION: str = "v1.0.0"
    JOB_NO_PREFIX: str = "J"  # e.g. J0001, J0002
    UPLOADS_DIR: str = "uploads"  # relative to backend root or absolute path
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_FROM_EMAIL: str = ""
    SMTP_TIMEOUT_SECONDS: int = 20

    class Config:
        env_file = [str(p) for p in _env_files]
        extra = "ignore"  # allow POSTGRES_* etc. in .env without defining them

settings = Settings()
