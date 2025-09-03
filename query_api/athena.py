import time
from typing import Any, Dict, List
import boto3
from botocore.exceptions import ClientError, ProfileNotFound
from .config import settings

def _make_session():
    try:
        return boto3.Session(profile_name=settings.aws_profile, region_name=settings.aws_region) if settings.aws_profile else boto3.Session(region_name=settings.aws_region)
    except ProfileNotFound:
        # fall back to default provider chain (env vars, SSO, instance role, etc.)
        return boto3.Session(region_name=settings.aws_region)

_session = _make_session()
_athena = _session.client("athena")
_glue = _session.client("glue")

def run_query(query: str, database: str | None, workgroup: str | None, output_s3: str | None) -> Dict[str, Any]:
    """Run SQL in Athena and return rows/metadata. Minimal and synchronous."""
    params: Dict[str, Any] = {}
    if database:
        params["QueryExecutionContext"] = {"Database": database}
    if output_s3:
        params["ResultConfiguration"] = {"OutputLocation": output_s3}
    if workgroup:
        params["WorkGroup"] = workgroup

    resp = _athena.start_query_execution(QueryString=query, **params)
    qid = resp["QueryExecutionId"]

    # Poll until done
    while True:
        info = _athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
        state = info["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(0.4)

    if state != "SUCCEEDED":
        raise RuntimeError(f"Athena error: {state}: {info['Status'].get('StateChangeReason', 'Unknown reason')}")

    # Fetch results
    res = _athena.get_query_results(QueryExecutionId=qid)
    cols = [c["Name"] for c in res["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]
    rows: List[Dict[str, Any]] = []
    for i, row in enumerate(res["ResultSet"]["Rows"]):
        if i == 0 and len(row.get("Data", [])) == len(cols):
            # skip header row
            continue
        cells = [d.get("VarCharValue") for d in row.get("Data", [])]
        rows.append({c: v for c, v in zip(cols, cells)})

    stats = info.get("Statistics", {})
    output_loc = info["ResultConfiguration"]["OutputLocation"]
    return {
        "columns": cols,
        "rows": rows,
        "row_count": len(rows),
        "bytes_scanned": stats.get("DataScannedInBytes"),
        "engine_ms": stats.get("EngineExecutionTimeInMillis"),
        "output": output_loc,
        "query_execution_id": qid,
    }

def list_tables(database: str) -> list[str]:
    names: list[str] = []
    paginator = _glue.get_paginator("get_tables")
    for page in paginator.paginate(DatabaseName=database):
        names.extend([t["Name"] for t in page.get("TableList", [])])
    return names
