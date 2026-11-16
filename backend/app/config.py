from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    sylus_owner_token: str
    app_env: str = "development"
    model_api_base_url: str = ""
    model_api_key: str = ""
    model_name: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
