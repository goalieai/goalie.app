from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    google_api_key: str = ""
    opik_api_key: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    openai_api_key: str = ""
    
    # Email (Resend)
    resend_api_key: str = ""
    resend_from_email: str = "Goalie AI <onboarding@resend.dev>"  # Default Resend test email
    
    # Frontend URL (for email links)
    frontend_url: str = "http://localhost:5173"

    # Google OAuth (for Calendar integration)
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/api/google/callback"
    frontend_origin: str = "http://localhost:5173"

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
    llm_primary_model: str = "gemini-3-flash-preview"
    llm_primary_temperature: float = 0.0
    llm_primary_max_retries: int = 1

    # Fallback model (used when primary hits rate limit)
    # Using Ollama for local inference (no rate limits!)
    # Format: "ollama:model_name" - e.g. ollama:llama3.2:1b, ollama:gemma2:2b
    llm_fallback_model: str = "ollama:llama3.2:1b"
    llm_fallback_temperature: float = 0.0
    llm_fallback_max_retries: int = 2

    # Conversational temperature (for chat responses)
    llm_conversational_temperature: float = 0.7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
