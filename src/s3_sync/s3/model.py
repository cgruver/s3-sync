import re
from enum import Enum
from functools import cached_property
from typing import TYPE_CHECKING
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError

if TYPE_CHECKING:
    from types_boto3_s3.client import S3Client
else:
    S3Client = object


_s3_pattern: re.Pattern = re.compile(
    r"^s3a?://"
    r"(?=[a-z0-9])"  # Bucket name must start with a letter or digit
    r"(?!(^xn--|sthree-|sthree-configurator|.+-s3alias$))"  # Bucket name must not start with xn--, sthree-, sthree-configurator or end with -s3alias
    r"(?!.*\.\.)"  # Bucket name must not contain two adjacent periods
    r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]"  # Bucket naming constraints
    r"(?<!\.-$)"  # Bucket name must not end with a period followed by a hyphen
    r"(?<!\.$)"  # Bucket name must not end with a period
    r"(?<!-$)"  # Bucket name must not end with a hyphen
    r"(/([a-zA-Z0-9._-]+/?)*)?$"  # key naming constraints
)

_bucket_and_key_pattern: re.Pattern = re.compile(
    r"^s3a?://"
    r"(?P<bucket>"  # Start of bucket named group
    r"(?=[a-z0-9])"
    r"(?!"
    r"(xn--|sthree-|sthree-configurator|.+-s3alias$)"
    r")"
    r"(?!.*\.\.)"
    r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]"
    r"(?<!\.-$)"
    r"(?<!\.$)"
    r"(?<!-$)"
    r")"  # End of bucket named group
    r"(?:/(?P<key>.*))?$"  # Start of key named group (optional)
)


class S3Path(BaseModel):
    """Pydantic Model for S3 URLs."""

    url: str = Field(
        ...,
        pattern=_s3_pattern,
        min_length=8,
        max_length=1023,
        description="An S3 path must start with s3:// or s3a:// and conform to S3 URL specifications.",
    )

    @property
    def fast_url(self) -> str:
        """Get the S3 URL but using the s3a:// protocol."""
        if self.scheme == "s3a":
            return self.url
        else:
            return f"s3a://{self.bucket}/{self.key}"

    @property
    def scheme(self) -> str:
        """Extract the scheme from the URL."""
        return self.url.split("://", 1)[0]

    @property
    def bucket(self) -> str:
        """Extract the bucket name from the URL."""
        match = _bucket_and_key_pattern.match(self.url)
        if match is None:
            raise ValidationError(f"Unable to parse bucket from {self.url}")
        return match.group("bucket")

    @property
    def is_dir(self) -> bool:
        """Check if the URL is a directory."""
        return self.url.endswith("/")

    @property
    def key(self) -> str:
        """Extract the key from the URL, if present."""
        match = _bucket_and_key_pattern.match(self.url)
        if match is None:
            raise ValidationError(f"Unable to parse key from {self.url}")
        key = match.group("key")
        return key

    @property
    def parent(self) -> Optional["S3Path"]:
        """Extract the parent key from the URL, if present."""
        match = _bucket_and_key_pattern.match(self.url)
        if match is None:
            return None
        key = match.group("key")
        if key:
            key_parts = key.removesuffix("/").rsplit("/", 1)
            if len(key_parts) == 1:
                return S3Path(url=f"{self.scheme}://{self.bucket}/")
            else:
                return S3Path(url=f"{self.scheme}://{self.bucket}/{key_parts[0]}/")
        return None


class S3File(BaseModel):
    """Pydantic Model to represent a specific file, represented by a key, at an S3 endpoint."""

    path: S3Path
    size: int


class S3FileSyncType(str, Enum):
    SINGLE = "single"
    MULTIPART = "multi-part"


class S3FileSyncPlan(BaseModel):
    """Pydantic Model for representing synchronizing a single file in S3."""

    src: S3File
    dest: S3Path
    type: S3FileSyncType


class S3Sync(BaseModel):
    """Pydantic Model for representing S3 synchronization."""

    src: S3Path
    dest: S3Path
    src_client: S3Client
    dest_client: S3Client
    chunk_size: int = 15_728_640

    @cached_property
    def src_objects(self) -> List[S3File]:
        ret = []
        for entry in self.src_client.list_objects(Bucket=self.src.bucket, Prefix=self.src.key).get("Contents", []):
            key = entry.get("Key", None)
            if key is not None:
                path = S3Path(url=f"{self.src.scheme}://{self.src.bucket}/{key}")
                size = self.src_client.head_object(Bucket=self.src.bucket, Key=key).get("ContentLength", 0)
                ret.append(S3File(path=path, size=size))
        return ret

    @cached_property
    def plans(self) -> List[S3FileSyncPlan]:
        ret = []
        for src_file in self.src_objects:
            trimmed_key = src_file.path.key.replace(self.src.key, "")
            dest_path = S3Path(url=f"{self.dest.url}{trimmed_key}")
            if src_file.size < self.chunk_size:
                sync_type = S3FileSyncType.SINGLE
            else:
                sync_type = S3FileSyncType.MULTIPART

            ret.append(S3FileSyncPlan(src=src_file, dest=dest_path, type=sync_type))
        return ret

    def _single_file_sync(self, src: S3Path, dest: S3Path):
        request = self.src_client.get_object(Bucket=src.bucket, Key=src.key)
        body = request.get("Body", None)
        if body is None:
            raise RuntimeError(f"Error retrieving {src} from {self.src_client.meta.endpoint_url}")
        self.dest_client.put_object(Bucket=dest.bucket, Key=dest.key)
