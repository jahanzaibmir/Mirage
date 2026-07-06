import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from .config import MirageConfig
from .geo import build_location_summary, lookup_geo
from .logger import HoneypotLogger


def log_attacker_event(logger: HoneypotLogger, source_ip: str) -> None:
    geo = lookup_geo(source_ip)
    summary = build_location_summary(geo)
    summary["public_ip"] = source_ip
    logger.record_event("attacker_seen", source_ip=source_ip, **summary)
    location = f"{summary['city']}, {summary['region']} {summary['country']}"
    if location.strip() == ",  unknown":
        location = "unknown"
    print(f"[ATTACKER] IP={source_ip} | Public={summary['public_ip']} | Location={location}")


class MirageHTTPServer(HTTPServer):
    def server_bind(self) -> None:
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

    def server_activate(self) -> None:
        self.socket.listen(5)


class MirageHTTPHandler(BaseHTTPRequestHandler):
    def _extract_source_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For") or self.headers.get("X-Real-IP")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def do_GET(self):
        source_ip = self._extract_source_ip()
        log_attacker_event(self.server.logger, source_ip)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        body = b"Mirage Honeypot active. No legitimate service here."
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


class MirageTCPServer:
    def __init__(self, config: MirageConfig, logger: HoneypotLogger) -> None:
        self.config = config
        self.logger = logger

    def run(self) -> None:
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind((self.config.host, self.config.tcp_port))
        self.tcp_socket.listen(5)
        self.logger.record_event("tcp_listening", host=self.config.host, port=self.config.tcp_port)

        while True:
            conn, addr = self.tcp_socket.accept()
            source_ip = addr[0]
            self.logger.record_event("tcp_connection", source_ip=source_ip, port=addr[1])
            log_attacker_event(self.logger, source_ip)
            conn.sendall(b"Mirage honeypot\n")
            conn.close()


class MirageHTTPService:
    def __init__(self, config: MirageConfig, logger: HoneypotLogger) -> None:
        self.config = config
        self.logger = logger

    def run(self) -> None:
        httpd = MirageHTTPServer((self.config.host, self.config.http_port), MirageHTTPHandler)
        httpd.logger = self.logger
        self.logger.record_event("http_listening", host=self.config.host, port=self.config.http_port)
        httpd.serve_forever()


def start_services(config: MirageConfig, logger: HoneypotLogger) -> None:
    http_server = MirageHTTPService(config, logger)
    tcp_server = MirageTCPServer(config, logger)

    threads = [
        threading.Thread(target=http_server.run, daemon=True),
        threading.Thread(target=tcp_server.run, daemon=True),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


def main() -> None:
    config = MirageConfig.from_env()
    logger = HoneypotLogger(log_dir=config.log_dir)
    logger.record_event("startup", message=config.banner)
    print(f"Mirage honeypot starting on http:{config.http_port} tcp:{config.tcp_port}")
    start_services(config, logger)
