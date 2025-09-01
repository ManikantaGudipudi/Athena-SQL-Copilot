# setup/seed.py
import os
import time
import requests
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from botocore.exceptions import ProfileNotFound


# Load ../.env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# -------- Config from env (with sane defaults) --------
REGION = os.getenv("AWS_REGION", "us-east-1")
PROFILE = os.getenv("AWS_PROFILE")  # e.g., "default" or None to use default chain
S3_BUCKET = os.environ["S3_BUCKET"]           # <-- must exist already
S3_PREFIX = os.getenv("S3_PREFIX", "athena-copilot")
GLUE_DB   = os.getenv("GLUE_DATABASE", "nyc_taxi_db")

RAW_PREFIX     = f"{S3_PREFIX}/raw/nyc_taxi/2019/01/"
CRAWLER_NAME   = f"{S3_PREFIX}-crawler"

# ~128MB .csv.gz (good size for Glue/Athena)
CSV_URL = "https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2019-01.csv.gz"
# Optional small lookup table (handy later)
ZONES_URL = "https://github.com/DataTalksClub/nyc-tlc-data/releases/download/misc/taxi_zone_lookup.csv"

# -------- Boto3 clients --------
try:
    _session = boto3.Session(profile_name=PROFILE, region_name=REGION) if PROFILE else boto3.Session(region_name=REGION)
except ProfileNotFound:
    print(f"[warn] AWS profile '{PROFILE}' not found; falling back to default credential chain.")
    _session = boto3.Session(region_name=REGION)
s3 = _session.client("s3")
glue = _session.client("glue")

# -------- Helpers --------
def ensure_bucket_exists(bucket: str):
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"[ok] Bucket exists: {bucket}")
    except ClientError as e:
        raise RuntimeError(f"S3 bucket '{bucket}' not found or not accessible: {e}")

def upload_stream(bucket: str, key: str, url: str):
    print(f"Downloading: {url}")
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        # Ensure raw stream decompresses if needed
        r.raw.decode_content = True
        s3.upload_fileobj(r.raw, bucket, key)
    size = s3.head_object(Bucket=bucket, Key=key)["ContentLength"]
    print(f"[ok] Uploaded s3://{bucket}/{key} ({size} bytes)")

def ensure_glue_db(name: str):
    try:
        glue.get_database(Name=name)
        print(f"[ok] Glue DB exists: {name}")
    except glue.exceptions.EntityNotFoundException:
        glue.create_database(DatabaseInput={"Name": name})
        print(f"[ok] Created Glue DB: {name}")

def ensure_crawler(name: str, db: str, s3_target: str):
    role = "AWSGlueServiceRoleDefault"  # adjust if your role name differs
    try:
        glue.get_crawler(Name=name)
        glue.update_crawler(
            Name=name,
            Role=role,
            DatabaseName=db,
            Targets={"S3Targets": [{"Path": s3_target}]},
        )
        print(f"[ok] Updated Crawler: {name}")
    except glue.exceptions.EntityNotFoundException:
        glue.create_crawler(
            Name=name,
            Role=role,
            DatabaseName=db,
            Targets={"S3Targets": [{"Path": s3_target}]},
        )
        print(f"[ok] Created Crawler: {name}")

def run_crawler_wait(name: str):
    glue.start_crawler(Name=name)
    print("[…] Crawler started, waiting…")
    while True:
        time.sleep(10)
        state = glue.get_crawler(Name=name)["Crawler"]["State"]
        if state == "READY":
            print("[ok] Crawler finished.")
            break
        print("   …still running")

def list_tables(db: str):
    names = []
    paginator = glue.get_paginator("get_tables")
    for page in paginator.paginate(DatabaseName=db):
        for t in page.get("TableList", []):
            names.append(t["Name"])
    return names

def main():
    ensure_bucket_exists(S3_BUCKET)

    # Upload data
    upload_stream(S3_BUCKET, f"{RAW_PREFIX}yellow_tripdata_2019-01.csv.gz", CSV_URL)
    # Optional: zones lookup
    upload_stream(S3_BUCKET, f"{S3_PREFIX}/raw/nyc_taxi/lookup/taxi_zone_lookup.csv", ZONES_URL)

    # Glue DB + Crawler
    ensure_glue_db(GLUE_DB)
    s3_path = f"s3://{S3_BUCKET}/{S3_PREFIX}/raw/nyc_taxi/"
    ensure_crawler(CRAWLER_NAME, GLUE_DB, s3_path)
    run_crawler_wait(CRAWLER_NAME)

    # Print discovered tables & a ready-to-run query
    tbls = list_tables(GLUE_DB)
    print("\n[ok] Tables in Glue DB:", tbls)
    if tbls:
        print("\nTry this in Athena (set workgroup & DB first):")
        print(f'SELECT * FROM "{GLUE_DB}"."{tbls[0]}" LIMIT 10;')

if __name__ == "__main__":
    main()
