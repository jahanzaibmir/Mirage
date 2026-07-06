import os
from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass
class MirageConfig:
    host: str = "0.0.0.0"
    http_port: int = 8080
    tcp_port: int = 2222
    log_dir: str = "logs"
    banner: str = "Mirage Honeypot ready"

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "MirageConfig":
        values = os.environ if env is None else env
        config = cls()
        if "MIRAGE_HOST" in values:
            config.host = values["MIRAGE_HOST"]
        if "MIRAGE_HTTP_PORT" in values:
            config.http_port = int(values["MIRAGE_HTTP_PORT"])
        if "MIRAGE_TCP_PORT" in values:
            config.tcp_port = int(values["MIRAGE_TCP_PORT"])
        if "MIRAGE_LOG_DIR" in values:
            config.log_dir = values["MIRAGE_LOG_DIR"]
        if "MIRAGE_BANNER" in values:
            config.banner = values["MIRAGE_BANNER"]
        return config
