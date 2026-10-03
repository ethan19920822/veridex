from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./veridex.db"
    veridex_user_agent: str = "VeridexAlpha/0.1 (+internal-regulatory-monitor)"
    http_timeout_seconds: int = 25
    max_links_per_source: int = 15

    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    host: str = "127.0.0.1"
    port: int = 8787

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_base_url and self.llm_api_key and self.llm_model)


settings = Settings()
