import os
from pathlib import Path

from dynaconf import Dynaconf

from .helpers import Truthy

skip_load = bool(Truthy(os.getenv("S3_SYNC_SKIP_LOAD_FILES", "false")))

default_config = Path(__file__).parent.joinpath("defaults.toml")
system_configs = [
    Path("/usr/share/s3-sync/config.toml"),
    Path("/etc/s3-sync/config.toml"),
]
user_config = Path(os.getenv("XDG_CONFIG_HOME", "~/.config")).expanduser().joinpath("s3-sync", "config.toml")
running_config = Path.cwd().joinpath("config.toml")
include_configs = system_configs + [user_config, running_config]

if skip_load:
    settings = Dynaconf(
        envvar_prefix="S3_SYNC",
        core_loaders=["TOML"],
        settings_files=[default_config],
        load_dotenv=False,
    )
else:
    settings = Dynaconf(
        envvar_prefix="S3_SYNC",
        core_loaders=["TOML"],
        settings_files=[default_config],
        load_dotenv=True,
        includes=include_configs,
    )
