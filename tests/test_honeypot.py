import tempfile
import unittest
from pathlib import Path

from mirage.config import MirageConfig
from mirage.geo import build_location_summary
from mirage.logger import HoneypotLogger
from storefront.app import create_admin_app, create_app


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

    def test_storefront_logs_request_details(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "storefront.db"
            app = create_app(
                {
                    "TESTING": True,
                    "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
                    "MIRAGE_LOG_DIR": tmpdir,
                }
            )
            with app.app_context():
                client = app.test_client()
                response = client.get(
                    "/login",
                    headers={"User-Agent": "Mozilla/5.0", "X-Forwarded-For": "203.0.113.10"},
                )

                self.assertEqual(response.status_code, 200)
                events_file = Path(tmpdir) / "events.jsonl"
                self.assertTrue(events_file.exists())

                content = events_file.read_text(encoding="utf-8")
                self.assertIn("http_request", content)
                self.assertIn("203.0.113.10", content)
                self.assertIn("/login", content)

                from storefront.app import db

                db.session.remove()
                db.engine.dispose()

    def test_admin_attacks_dashboard_shows_request_details(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "storefront.db"
            app = create_admin_app(
                {
                    "TESTING": True,
                    "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
                    "MIRAGE_LOG_DIR": tmpdir,
                    "MIRAGE_ADMIN_PATH": "/hidden-ops",
                }
            )
            with app.app_context():
                client = app.test_client()
                login_response = client.post(
                    "/hidden-ops/login",
                    data={"email": "admin@example.com", "password": "adminpass"},
                    follow_redirects=True,
                )
                self.assertEqual(login_response.status_code, 200)

                client.get(
                    "/hidden-ops/login",
                    headers={"User-Agent": "Mozilla/5.0", "X-Forwarded-For": "198.51.100.7"},
                )

                dashboard_response = client.get("/hidden-ops/attacks", follow_redirects=True)
                self.assertEqual(dashboard_response.status_code, 200)
                body = dashboard_response.get_data(as_text=True)
                self.assertIn("Threat Overview", body)
                self.assertIn("Attacker Activity", body)
                self.assertIn("198.51.100.7", body)
                self.assertIn("Location", body)

                from storefront.app import db

                db.session.remove()
                db.engine.dispose()

    def test_admin_can_clear_previous_activity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "storefront.db"
            app = create_admin_app(
                {
                    "TESTING": True,
                    "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
                    "MIRAGE_LOG_DIR": tmpdir,
                    "MIRAGE_ADMIN_PATH": "/hidden-ops",
                }
            )
            with app.app_context():
                client = app.test_client()
                client.post(
                    "/hidden-ops/login",
                    data={"email": "admin@example.com", "password": "adminpass"},
                    follow_redirects=True,
                )
                app.extensions["honeypot_logger"].record_event(
                    "http_request",
                    source_ip="9.9.9.9",
                    path="/admin",
                    method="GET",
                )

                response = client.post("/hidden-ops/clear", follow_redirects=True)
                self.assertEqual(response.status_code, 200)

                events_file = Path(tmpdir) / "events.jsonl"
                self.assertTrue(events_file.exists())
                self.assertEqual(events_file.read_text(encoding="utf-8").strip(), "")

                from storefront.app import db

                db.session.remove()
                db.engine.dispose()

    def test_admin_dashboard_redirects_to_admin_console(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "storefront.db"
            app = create_app(
                {
                    "TESTING": True,
                    "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
                    "MIRAGE_LOG_DIR": tmpdir,
                    "MIRAGE_ADMIN_PATH": "/hidden-ops",
                    "MIRAGE_ADMIN_BASE_URL": "http://127.0.0.1:5001",
                }
            )
            with app.app_context():
                client = app.test_client()
                client.post(
                    "/login",
                    data={"email": "admin@example.com", "password": "adminpass"},
                )
                response = client.get("/dashboard")
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers["Location"], "http://127.0.0.1:5001/hidden-ops/attacks")

                from storefront.app import db

                db.session.remove()
                db.engine.dispose()

    def test_public_app_does_not_expose_admin_surface(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "storefront.db"
            app = create_app(
                {
                    "TESTING": True,
                    "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
                    "MIRAGE_LOG_DIR": tmpdir,
                    "MIRAGE_ADMIN_PATH": "/hidden-ops",
                }
            )
            with app.app_context():
                client = app.test_client()
                response = client.get("/hidden-ops/attacks")
                self.assertEqual(response.status_code, 404)

                from storefront.app import db

                db.session.remove()
                db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
