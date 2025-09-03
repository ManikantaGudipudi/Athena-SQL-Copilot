import os
from pydantic import BaseModel

class Settings(BaseModel):
    # AWS
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_profile: str | None = os.getenv("AWS_PROFILE")  # use your 'copilot-dev' profile
    glue_database: str = os.getenv("GLUE_DATABASE", "nyc_taxi_db")

    # LLM (OpenAI-compatible, works with vLLM or OpenAI)
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8001/v1")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "dummy")
    model: str = os.getenv("LLM_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")

    # Optional execution via Chunk 2 API
    query_api_base: str | None = os.getenv("QUERY_API_BASE")  # e.g., http://127.0.0.1:8000

settings = Settings()
