import os
from typing import Callable

import boto3
from boto3.s3.transfer import TransferConfig
from pydantic import AnyHttpUrl

from ..util import logger
from ..util import settings
from .model import S3Path
from .model import S3Sync


def sync(
    src: S3Path,
    dest: S3Path,
    src_endpoint: AnyHttpUrl = AnyHttpUrl(settings.src.endpoint),
    dest_endpoint: AnyHttpUrl = AnyHttpUrl(settings.dest.endpoint),
    src_region: str = settings.src.region,
    dest_region: str = settings.dest.region,
    src_validate: bool = settings.src.validate_tls,
    dest_validate: bool = settings.dest.validate_tls,
    max_threads_per_file: int = 5,
    max_files: int = 1,
    chunk_size: int = 15_728_640,
    printer: Callable = print,
) -> None:
    src_access_key = settings.src.access_key
    src_secret_key = settings.src.secret_key
    if src_access_key is None or src_access_key == "":
        src_access_key = os.getenv("AWS_ACCESS_KEY_ID", None)
    if src_secret_key is None or src_secret_key == "":
        src_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", None)
    src_client = boto3.client(
        "s3",
        endpoint_url=str(src_endpoint),
        region_name=src_region,
        verify=src_validate,
        aws_access_key_id=src_access_key,
        aws_secret_access_key=src_secret_key,
    )
    dest_access_key = settings.dest.access_key
    dest_secret_key = settings.dest.secret_key
    if dest_access_key is None or dest_access_key == "":
        dest_access_key = os.getenv("AWS_ACCESS_KEY_ID", None)
    if dest_secret_key is None or dest_secret_key == "":
        dest_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", None)
    dest_client = boto3.client(
        "s3",
        endpoint_url=str(dest_endpoint),
        region_name=dest_region,
        verify=dest_validate,
        aws_access_key_id=dest_access_key,
        aws_secret_access_key=dest_secret_key,
    )
    transfer_config = TransferConfig(
        multipart_chunksize=chunk_size,
        multipart_threshold=chunk_size,
        max_concurrency=max_threads_per_file,
        preferred_transfer_client="classic",
    )
    sync = S3Sync(
        src=src,
        dest=dest,
        src_client=src_client,
        dest_client=dest_client,
        transfer_config=transfer_config,
        max_files=max_files,
    )
    logger.debug(f"Synchronization plan: {sync.plans}")
    for line in sync.execute():
        printer(line)
