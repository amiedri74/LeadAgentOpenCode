from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://leadagent:leadagent_secret_2026@localhost:5433/leadagent"
    redis_url: str = "redis://localhost:6379/0"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    hunter_api_key: str = ""
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = ""
    permit_api_base: str = "https://data.lacity.org/resource/hbkd-qubn.json"
    app_name: str = "Amy Electric Lead Agent"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000", "http://localhost"]

    tier1_zips: list[str] = [
        "91367", "91302", "91316", "91436", "91403", "91423", "90210"
    ]
    tier2_zips: list[str] = [
        "90265", "90401", "90402", "90403", "90404", "90405",
        "91201", "91202", "91203", "91204", "91205", "91206",
        "91207", "91208", "91214", "91101", "91103", "91104",
        "91105", "91106", "91107", "91501", "91502", "91504",
        "91505", "91506"
    ]

    class Config:
        env_file = ".env"


settings = Settings()
