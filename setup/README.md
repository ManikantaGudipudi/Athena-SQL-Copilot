# CHUNK1_SETUP
Seed NYC Taxi (one month) to S3 and create Glue DB + Crawler.


## Prereqs
- AWS CLI configured (profile in .env)
- Python 3.11, `pip install boto3 python-dotenv requests`


## Run
export $(grep -v '^#' ../.env | xargs) # or use direnv
python seed.py


This will:
1) Download small NYC Yellow Taxi sample.
2) Upload to s3://${S3_BUCKET}/${S3_PREFIX}/raw/nyc_taxi/2019/01/
3) Create Glue DB ${GLUE_DATABASE} (idempotent).
4) Create & run a Glue Crawler over s3://${S3_BUCKET}/${S3_PREFIX}/raw/nyc_taxi/
5) Wait for crawler to finish.
6) Print Athena preview query you can try in the console.