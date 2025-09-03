from typing import Dict, List
import boto3
from botocore.exceptions import ProfileNotFound
from .config import settings

def _make_session():
    try:
        return boto3.Session(profile_name=settings.aws_profile, region_name=settings.aws_region) if settings.aws_profile else boto3.Session(region_name=settings.aws_region)
    except ProfileNotFound:
        return boto3.Session(region_name=settings.aws_region)

_session = _make_session()
_glue = _session.client("glue")

def get_tables_and_columns(database: str) -> List[Dict]:
    """Return [{'table': str, 'columns': [str], 'partitions': [str]}...]"""
    out: List[Dict] = []
    paginator = _glue.get_paginator("get_tables")
    for page in paginator.paginate(DatabaseName=database):
        for t in page.get("TableList", []):
            name = t["Name"]
            cols = [c["Name"] for c in t.get("StorageDescriptor", {}).get("Columns", [])]
            parts = [p["Name"] for p in t.get("PartitionKeys", [])]
            out.append({"table": name, "columns": cols, "partitions": parts})
    return out
