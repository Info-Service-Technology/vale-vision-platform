import os
from pathlib import Path

import boto3


AWS_REGION = os.getenv("AWS_REGION", "sa-east-1")
LOCAL_INPUT_DIR = Path(os.getenv("LOCAL_INPUT_DIR", "/tmp/vale-vision/input"))
LOCAL_OUTPUT_DIR = Path(os.getenv("LOCAL_OUTPUT_DIR", "/tmp/vale-vision/output"))

s3 = boto3.client("s3", region_name=AWS_REGION)


def download_s3_object(bucket: str, key: str) -> Path:
    LOCAL_INPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = Path(key).name
    local_path = LOCAL_INPUT_DIR / filename

    s3.download_file(bucket, key, str(local_path))

    return local_path


def upload_debug_file(bucket: str, local_path: Path, output_key: str) -> str:
    s3.upload_file(str(local_path), bucket, output_key)
    return output_key