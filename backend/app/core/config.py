from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: str = ""
    opik_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
