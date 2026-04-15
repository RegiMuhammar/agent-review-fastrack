from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Laravel Communication
    LARAVEL_URL: str = "http://localhost:8000"
    INTERNAL_KEY: str = "super-secret-internal-key"
    
    # LLM API Keys
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""  # Opsional
    TAVILY_API_KEY: str = ""

    # File retrieval
    # PDF diambil dari endpoint internal Laravel (local storage),
    # jadi tidak perlu konfigurasi object storage di ai-agent.

    # LangSmith (opsional tracing)
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()