from pydantic import BaseModel
import os

class Settings(BaseModel):
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_profile: str | None = os.getenv("AWS_PROFILE")  # leave empty to use default chain
    glue_database: str = os.getenv("GLUE_DATABASE", "nyc_taxi_db")
    athena_workgroup: str = os.getenv("ATHENA_WORKGROUP", "primary")
    athena_output_s3: str | None = os.getenv("ATHENA_OUTPUT_S3")  # strongly recommended

settings = Settings()
