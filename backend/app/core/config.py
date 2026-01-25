from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    google_api_key: str = ""
    opik_api_key: str = ""

    # ==========================================================================
    # LLM Model Configuration
    # ==========================================================================
    # Free Tier Rate Limits (Requests Per Minute):
    #   - gemini-2.5-flash: 20 RPM (newest, smartest)
    #   - gemini-1.5-flash: 15 RPM (stable, best fallback)
    #   - gemini-2.0-flash: 10 RPM (preview)
    #   - gemini-1.5-pro:    2 RPM (complex reasoning, avoid for automation)
    # ==========================================================================

    # Primary model (used first)
    llm_primary_model: str = "gemini-2.5-flash"
    llm_primary_temperature: float = 0.0
    llm_primary_max_retries: int = 1

    # Fallback model (used when primary hits rate limit)
    llm_fallback_model: str = "	gemini-1.5-flash"
    llm_fallback_temperature: float = 0.0
    llm_fallback_max_retries: int = 2

    # Conversational temperature (for chat responses)
    llm_conversational_temperature: float = 0.7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
