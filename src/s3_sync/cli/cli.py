from typing import Optional

import typer
from pydantic import AnyHttpUrl
from pydantic import ValidationError
from rich import print
from typing_extensions import Annotated

from ..s3 import S3Path
from ..s3 import sync as s3_sync
from ..util import logger
from ..util import make_logger
from ..util import settings


def version_callback(value: bool):
    if value:
        from ..__version__ import version

        print(version)
        raise typer.Exit()


def parse_url(value: str) -> AnyHttpUrl:
    try:
        return AnyHttpUrl(value)
    except ValidationError:
        logger.error(f"Invalid endpoint URL: {value}")
        logger.error("Did you include a scheme (http:// or https://)?")
        raise


cli = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]},
    pretty_exceptions_show_locals=False,
    add_completion=False,
)


@cli.command(no_args_is_help=True)
def sync(
    src: Annotated[str, typer.Argument(help="The source bucket and folder to sync from")] = "",
    dest: Annotated[str, typer.Argument(help="The destination bucket and folder to sync to")] = "",
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            help="Increase logging verbosity (repeat for more)",
            show_default=False,
            metavar="",
        ),
    ] = 0,
    src_endpoint: Annotated[
        Optional[AnyHttpUrl],
        typer.Option(
            "--src-endpoint",
            "-s",
            help="The endpoint to use for the source bucket",
            parser=parse_url,
            metavar="URL",
        ),
    ] = None,
    dest_endpoint: Annotated[
        Optional[AnyHttpUrl],
        typer.Option(
            "--dest-endpoint",
            "-d",
            help="The endpoint to use for the destination bucket",
            parser=parse_url,
            metavar="URL",
        ),
    ] = None,
    src_region: Annotated[
        str,
        typer.Option(
            "--src-region",
            help="The region to use for the S3 client for the source",
        ),
    ] = settings.src.region,
    dest_region: Annotated[
        str,
        typer.Option(
            "--dest-region",
            help="The region to use for the S3 client for the destination",
        ),
    ] = settings.dest.region,
    src_validate: Annotated[
        bool,
        typer.Option(
            "--src-validate",
            help="Whether to validate the TLS certificates of the source endpoint, if applicable",
        ),
    ] = settings.src.validate_tls,
    dest_validate: Annotated[
        bool,
        typer.Option(
            "--src-validate",
            help="Whether to validate the TLS certificates of the destination endpoint, if applicable",
        ),
    ] = settings.dest.validate_tls,
    max_threads_per_file: Annotated[
        int,
        typer.Option(
            help="The maximum threads per S3 object sync, to adjust bandwidth in multipart operations",
        ),
    ] = settings.transfer_config.max_threads_per_file,
    max_files: Annotated[
        int,
        typer.Option(
            help="The maximum number of files to transfer at a time",
        ),
    ] = settings.transfer_config.max_files,
    chunk_size: Annotated[
        str,
        typer.Option(help="The size of each chunk", metavar="BYTESIZE"),
    ] = settings.transfer_config.chunk_size,
    _: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            help="Print the version and exit",
            is_eager=True,
            show_default=False,
        ),
    ] = False,
):
    """S3 bucket synchronization, buffered and multi-threaded.

    NOTE: For credentials, either load them in the ~/.aws/credentials, ~/.config/s3-sync/config.toml (which has separate
    sections for source and destination), or provide environment variables - either using the names you normally would,
    or as S3_SYNC_SRC__ACCESS_KEY/S3_SYNC_SRC__SECRET_KEY and S3_SYNC_DEST__ACCESS_KEY/S3_SYNC_DEST__SECRET_KEY. It is
    deliberate that there is no way to provide them on the command line.\
    """

    logger = make_logger(verbose)
    logger.debug(f"{src} -> {dest}")

    src_and_dest = dict()
    try:
        src_path = S3Path(url=src)
        src_and_dest["src"] = src_path
    except ValidationError:
        logger.error(
            f"Source path ('{src}') does not look like a valid S3 URL (s3://\[endpoint/]\[bucket/]\[path/]object)"  # noqa: W605
        )

    try:
        dest_path = S3Path(url=dest)
        src_and_dest["dest"] = dest_path
    except ValidationError:
        logger.error(
            f"Destination path ('{dest}') does not look like a valid S3 URL (s3://\[endpoint/]\[bucket/]\[path/]object)"  # noqa: W605
        )

    s3_sync(
        src_endpoint=src_endpoint,
        dest_endpoint=dest_endpoint,
        src_region=src_region,
        dest_region=dest_region,
        src_validate=src_validate,
        dest_validate=dest_validate,
        max_threads_per_file=max_threads_per_file,
        max_files=max_files,
        chunk_size=chunk_size,
        printer=print,
        **src_and_dest,
    )
