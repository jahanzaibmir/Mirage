import tempfile
import unittest
from pathlib import Path

from mirage.config import MirageConfig
from mirage.geo import build_location_summary
from mirage.logger import HoneypotLogger


class MirageTests(unittest.TestCase):
    def test_default_config_values(self):
        config = MirageConfig()
        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.http_port, 8080)
        self.assertEqual(config.tcp_port, 2222)

    def test_config_reads_environment_overrides(self):
        config = MirageConfig.from_env({"MIRAGE_HTTP_PORT": "9090", "MIRAGE_TCP_PORT": "2323"})
        self.assertEqual(config.http_port, 9090)
        self.assertEqual(config.tcp_port, 2323)

    def test_location_summary_uses_geo_fields(self):
        summary = build_location_summary({"ip": "8.8.8.8", "country": "US", "region": "California", "city": "Mountain View"})
        self.assertEqual(summary["public_ip"], "8.8.8.8")
        self.assertEqual(summary["country"], "US")
        self.assertEqual(summary["city"], "Mountain View")

    def test_logger_writes_event_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HoneypotLogger(log_dir=tmpdir)
            logger.record_event("probe", source_ip="10.0.0.5", port=2222)

            log_file = Path(tmpdir) / "mirage.log"
            events_file = Path(tmpdir) / "events.jsonl"
            self.assertTrue(log_file.exists())
            self.assertTrue(events_file.exists())

            content = events_file.read_text(encoding="utf-8")
            self.assertIn("10.0.0.5", content)


if __name__ == "__main__":
    unittest.main()
