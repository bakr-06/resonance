from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ollama_num_ctx: int = 8192
    ollama_timeout_seconds: float = 120.0
    db_user: str = "resonance"
    db_password: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "resonance"


settings = Settings()
