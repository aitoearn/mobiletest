from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Mobile Test AI"
    debug: bool = False
    
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mobile_test"
    redis_url: str = "redis://localhost:6379/0"
    
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    
    class Config:
        env_file = ".env"


settings = Settings()
