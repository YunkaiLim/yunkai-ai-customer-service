from ipaddress import ip_address
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")

    service_host: str = "127.0.0.1"
    service_port: int = 8000
    service_name: str = "Yunkai Customer Service"

    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen3:8b"
    llm_timeout_seconds: int = 180

    database_path: str = "./data/support.db"
    knowledge_dir: str = "./data/knowledge"
    max_history_messages: int = 10
    handoff_score_threshold: float = 0.12
    admin_token: str = ""

    chatwoot_base_url: str = ""
    chatwoot_account_id: str = ""
    chatwoot_api_token: str = ""
    chatwoot_webhook_secret: str = ""

    @field_validator("service_host")
    @classmethod
    def loopback_only(cls, value: str) -> str:
        if value == "localhost":
            return value
        try:
            if ip_address(value).is_loopback:
                return value
        except ValueError:
            pass
        raise ValueError("SERVICE_HOST must be loopback-only")

    @property
    def db_path(self) -> Path:
        return Path(self.database_path)

    @property
    def kb_dir(self) -> Path:
        return Path(self.knowledge_dir)


settings = Settings()
