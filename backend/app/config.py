from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    sylus_owner_token: str
    app_env: str = "development"
    model_api_base_url: str = ""
    model_api_key: str = ""
    model_name: str = "openai/gpt-oss-120b"
    # Optional no-cost provider credentials. Empty means provider is not used.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    gemini_fallback_model: str = "gemini-3.5-flash-lite"
    gemini_vision_model: str = "gemini-3.8-flash"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_fallback_model: str = "openai/gpt-oss-20b"
    aion_api_key: str = ""
    aion_model: str = "aion-labs/aion-rp-llama-3.1-8b"
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"
    openrouter_mature_model: str = ""
    cohere_api_key: str = ""
    cohere_model: str = "command-a-03-2025"
    cloudflare_chat_model: str = "@cf/meta/llama-3.1-8b-instruct-fp8-fast"
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    cloudflare_image_limit_24h: int = 10
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    sylus_owner_password: str = ""
    session_secret: str = ""
    session_ttl_seconds: int = 1209600
    web_push_vapid_public_key: str = ""
    web_push_vapid_private_key: str = ""
    web_push_vapid_subject: str = ""
    scheduler_secret: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
