from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .config import settings
from .athena import run_query, list_tables

app = FastAPI(title="Athena Mini Query API")

class SQLRequest(BaseModel):
    query: str
    database: str | None = settings.glue_database
    workgroup: str | None = settings.athena_workgroup

@app.get("/health")
def health():
    return {"ok": True, "region": settings.aws_region, "db": settings.glue_database}

@app.get("/tables")
def tables(db: str | None = None):
    try:
        return {"database": db or settings.glue_database, "tables": list_tables(db or settings.glue_database)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/sql")
def sql(req: SQLRequest):
    try:
        data = run_query(
            req.query,
            database=req.database,
            workgroup=req.workgroup,
            output_s3=settings.athena_output_s3,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
