from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    openrouter_api_key: str = ""
    db_user: str = "resonance"
    db_password: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "resonance"


settings = Settings()
