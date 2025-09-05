import os
from pydantic import BaseModel

class Settings(BaseModel):
    # Disable protected namespace warnings (fixes the autogen "model_client_cls" warning)
    model_config = {
        "protected_namespaces": ()
    }

    # AWS
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_profile: str | None = os.getenv("AWS_PROFILE")  # use your 'copilot-dev' profile
    glue_database: str = os.getenv("GLUE_DATABASE", "nyc_taxi_db")

    # LLM (OpenAI-compatible, works with vLLM or OpenAI)
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "dummy")
    model: str = os.getenv("LLM_MODEL", "deepseek-r1:7b")

    # Optional execution via Chunk 2 API
    query_api_base: str | None = os.getenv("QUERY_API_BASE", "http://127.0.0.1:8000")  # e.g., http://127.0.0.1:8000


settings = Settings()
