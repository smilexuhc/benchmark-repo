"""TOS object storage helpers.

TOS exposes an S3-compatible API, so boto3 keeps the storage layer small and
easy to run locally against any compatible endpoint.
"""
import os
import uuid

import boto3
from botocore.config import Config
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

TOS_BUCKET = os.getenv("TOS_BUCKET", "").strip()
TOS_REGION = os.getenv("TOS_REGION", "").strip()
TOS_ENDPOINT = os.getenv("TOS_ENDPOINT", "").strip()
TOS_ACCESS_KEY_ID = os.getenv("TOS_ACCESS_KEY_ID", "").strip()
TOS_SECRET_ACCESS_KEY = os.getenv("TOS_SECRET_ACCESS_KEY", "").strip()


def _require_config() -> None:
    missing = [
        name
        for name, value in [
            ("TOS_BUCKET", TOS_BUCKET),
            ("TOS_REGION", TOS_REGION),
            ("TOS_ENDPOINT", TOS_ENDPOINT),
            ("TOS_ACCESS_KEY_ID", TOS_ACCESS_KEY_ID),
            ("TOS_SECRET_ACCESS_KEY", TOS_SECRET_ACCESS_KEY),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError("Missing TOS configuration: " + ", ".join(missing))


def _client():
    _require_config()
    return boto3.client(
        "s3",
        endpoint_url=TOS_ENDPOINT,
        region_name=TOS_REGION,
        aws_access_key_id=TOS_ACCESS_KEY_ID,
        aws_secret_access_key=TOS_SECRET_ACCESS_KEY,
        config=Config(
            signature_version="s3v4",
            connect_timeout=10,
            read_timeout=60,
            retries={"max_attempts": 3, "mode": "standard"},
            s3={"addressing_style": "virtual"},
        ),
    )


def new_object_key(ext: str = ".png", prefix: str = "images") -> str:
    ext = ext if ext.startswith(".") else f".{ext}"
    return f"{prefix}/{uuid.uuid4().hex}{ext.lower()}"


def put_bytes(object_key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    _client().put_object(
        Bucket=TOS_BUCKET,
        Key=object_key,
        Body=data,
        ContentType=content_type,
    )
    return object_key


def get_bytes(object_key: str) -> bytes:
    obj = _client().get_object(Bucket=TOS_BUCKET, Key=object_key)
    return obj["Body"].read()


def delete_object(object_key: str) -> None:
    if object_key:
        _client().delete_object(Bucket=TOS_BUCKET, Key=object_key)


def object_url(object_key: str, expires: int = 3600) -> str:
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": TOS_BUCKET, "Key": object_key},
        ExpiresIn=expires,
    )


def health_check() -> bool:
    _client().head_bucket(Bucket=TOS_BUCKET)
    return True
