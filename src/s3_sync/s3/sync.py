import os

import boto3
from boto3.s3.transfer import TransferConfig
from boto3.s3.transfer import TransferManager
from pydantic import AnyHttpUrl

from ..util import logger
from ..util import settings
from .model import S3Path


def sync(
    src: S3Path,
    dest: S3Path,
    src_endpoint: AnyHttpUrl = AnyHttpUrl(settings.src.endpoint),
    dest_endpoint: AnyHttpUrl = AnyHttpUrl(settings.dest.endpoint),
    src_validate: bool = settings.src.validate_tls,
    dest_validate: bool = settings.dest.validate_tls,
    max_threads_per_conn: int = 5,
) -> None:
    config = TransferConfig(max_concurrency=max_threads_per_conn)
    src_access_key = settings.src.access_key
    src_secret_key = settings.src.secret_key
    if src_access_key is None:
        src_access_key = os.getenv("AWS_ACCESS_KEY_ID", None)
    if src_secret_key is None:
        src_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", None)
    src_client = boto3.client(
        "s3",
        endpoint_url=str(src_endpoint),
        verify=src_validate,
        aws_access_key_id=src_access_key,
        aws_secret_access_key=src_secret_key,
    )
    dest_access_key = settings.dest.access_key
    dest_secret_key = settings.dest.secret_key
    if dest_access_key is None:
        dest_access_key = os.getenv("AWS_ACCESS_KEY_ID", None)
    if dest_secret_key is None:
        dest_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", None)
    dest_client = boto3.client(
        "s3",
        endpoint_url=str(dest_endpoint),
        verify=dest_validate,
        aws_access_key_id=dest_access_key,
        aws_secret_access_key=dest_secret_key,
    )
    logger.debug(f"{src_client} -> {dest_client}")
