from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    PROJECT_NAME: str = "PPP API"
    DATABASE_URL: str = "mysql+pymysql://user:password@db:3306/ppplanner"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
