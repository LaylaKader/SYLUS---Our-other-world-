from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    sylus_owner_token: str
    app_env: str = "development"
    model_api_base_url: str = ""
    model_api_key: str = ""
    model_name: str = "openai/gpt-oss-120b"
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    cloudflare_image_limit_24h: int = 10
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    sylus_owner_password: str = ""
    session_secret: str = ""
    session_ttl_seconds: int = 1209600
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
