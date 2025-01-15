import pytest
from pydantic import ValidationError

from s3_sync.s3.model import S3Path


@pytest.mark.parametrize(
    "url,expected_bucket,expected_key,expected_parent,expected_scheme,expected_is_dir",
    [
        ("s3://my-bucket/", "my-bucket", "", None, "s3", True),
        ("s3://my.bucket.name/my-key", "my.bucket.name", "my-key", S3Path(url="s3://my.bucket.name/"), "s3", False),
        (
            "s3://123-bucket/another/key/path",
            "123-bucket",
            "another/key/path",
            S3Path(url="s3://123-bucket/another/key/"),
            "s3",
            False,
        ),
        (
            "s3://bucket/this/is/a/folder/",
            "bucket",
            "this/is/a/folder/",
            S3Path(url="s3://bucket/this/is/a/"),
            "s3",
            True,
        ),
        (
            "s3://my-bucket/some/key/path/file.txt",
            "my-bucket",
            "some/key/path/file.txt",
            S3Path(url="s3://my-bucket/some/key/path/"),
            "s3",
            False,
        ),
        (
            "s3://10-bucket-01/nested.folder/structure/file.jpg",
            "10-bucket-01",
            "nested.folder/structure/file.jpg",
            S3Path(url="s3://10-bucket-01/nested.folder/structure/"),
            "s3",
            False,
        ),
        ("s3://my-bucket/with-key", "my-bucket", "with-key", S3Path(url="s3://my-bucket/"), "s3", False),
        ("s3a://my-bucket/", "my-bucket", "", None, "s3a", True),
        ("s3a://my.bucket.name/my-key", "my.bucket.name", "my-key", S3Path(url="s3a://my.bucket.name/"), "s3a", False),
        (
            "s3a://123-bucket/another/key/path",
            "123-bucket",
            "another/key/path",
            S3Path(url="s3a://123-bucket/another/key/"),
            "s3a",
            False,
        ),
        (
            "s3a://bucket/this/is/a/folder/",
            "bucket",
            "this/is/a/folder/",
            S3Path(url="s3a://bucket/this/is/a/"),
            "s3a",
            True,
        ),
        (
            "s3a://my-bucket/some/key/path/file.txt",
            "my-bucket",
            "some/key/path/file.txt",
            S3Path(url="s3a://my-bucket/some/key/path/"),
            "s3a",
            False,
        ),
        (
            "s3a://10-bucket-01/nested.folder/structure/file.jpg",
            "10-bucket-01",
            "nested.folder/structure/file.jpg",
            S3Path(url="s3a://10-bucket-01/nested.folder/structure/"),
            "s3a",
            False,
        ),
        ("s3a://my-bucket/with-key", "my-bucket", "with-key", S3Path(url="s3a://my-bucket/"), "s3a", False),
    ],
)
def test_good_s3_paths(
    url: str,
    expected_bucket: str,
    expected_key: str,
    expected_parent: S3Path,
    expected_scheme: str,
    expected_is_dir: bool,
) -> None:
    path = S3Path(url=url)
    dump_url = path.model_dump()["url"]
    assert dump_url == url
    assert path.bucket == expected_bucket
    assert path.key == expected_key
    assert path.scheme == expected_scheme
    assert path.parent == expected_parent
    assert path.is_dir == expected_is_dir


@pytest.mark.parametrize(
    "url",
    [
        "s3://",
        "s3://my",
        "https://my-bucket/",
        "s3://bucket-name/with/white space/in/key",
        "s3:/my-bucket/",
        "s3://my_bucket/",
        "s3://My-Bucket/",
        "s3://123.bucketname./invalid",
        "s3://123.bucketname.-/invalid",
        "s3://123.bucket..name/invalid",
        "s3://-bucket-starts-with-hyphen/",
        "s3://bucket-ends-with-hyphen-/",
        "s3://my-bucket/ends/with/slash//",
        "s3://toolongnameofthebucketwhichexceedssixtyfourcharacterslongforthisexample/",
        "s3://my-bucket/?query=parameters",
        "s3://my-bucket/this/path/has/a/tab/char\there",
        "s3a://",
        "s3a://my",
        "s3a://bucket-name/with/white space/in/key",
        "s3a:/my-bucket/",
        "s3a://my_bucket/",
        "s3a://My-Bucket/",
        "s3a://123.bucketname./invalid",
        "s3a://123.bucketname.-/invalid",
        "s3a://123.bucket..name/invalid",
        "s3a://-bucket-starts-with-hyphen/",
        "s3a://bucket-ends-with-hyphen-/",
        "s3a://my-bucket/ends/with/slash//",
        "s3a://toolongnameofthebucketwhichexceedssixtyfourcharacterslongforthisexample/",
        "s3a://my-bucket/?query=parameters",
        "s3a://my-bucket/this/path/has/a/tab/char\there",
    ],
)
def test_bad_s3_paths(url: str) -> None:
    with pytest.raises(ValidationError):
        path = S3Path(url=url)
        _ = path.model_dump()["url"]
