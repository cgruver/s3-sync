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
)


@cli.command(no_args_is_help=True)
def sync(
    src: Annotated[str, typer.Argument(help="The source bucket and folder to sync from")],
    dest: Annotated[str, typer.Argument(help="The destination bucket and folder to sync to")],
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose", "-v", count=True, help="Increase logging verbosity (repeat for more)", show_default=False
        ),
    ] = 0,
    src_endpoint: Annotated[
        AnyHttpUrl,
        typer.Option(
            "--src-endpoint",
            "-s",
            help="The endpoint to use for the source bucket",
            parser=parse_url,
        ),
    ] = AnyHttpUrl(settings.src.endpoint),
    dest_endpoint: Annotated[
        AnyHttpUrl,
        typer.Option(
            "--dest-endpoint",
            "-d",
            help="The endpoint to use for the destination bucket",
            parser=parse_url,
        ),
    ] = AnyHttpUrl(settings.dest.endpoint),
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
    max_threads_per_conn: Annotated[
        int,
        typer.Option(
            help="The maximum threads per S3 object connection, to adjust bandwidth in multipart operations",
        ),
    ] = 5,
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
    try:
        src_path = S3Path(url=src)
    except ValidationError:
        print(
            f"Source path ('{src}') does not look like a valid S3 URL (s3://\[endpoint/]\[bucket/]\[path/]object)"  # noqa: W605
        )
        raise typer.Exit(1)

    try:
        dest_path = S3Path(url=dest)
    except ValidationError:
        print(
            f"Destination path ('{dest}') does not look like a valid S3 URL (s3://\[endpoint/]\[bucket/]\[path/]object)"  # noqa: W605
        )
        raise typer.Exit(1)

    logger.debug(f"{src_endpoint}{src_path.bucket}/{src_path.key} -> {dest_endpoint}{dest_path.bucket}/{dest_path.key}")
    s3_sync(
        src=src_path,
        dest=dest_path,
        src_endpoint=src_endpoint,
        dest_endpoint=dest_endpoint,
        src_validate=src_validate,
        dest_validate=dest_validate,
        max_threads_per_conn=max_threads_per_conn,
    )
