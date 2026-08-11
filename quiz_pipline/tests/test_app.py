import importlib
import os
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class AppDatabaseDefaultsTest(unittest.TestCase):
    def test_defaults_match_docker_setup(self):
        os.environ.pop("POSTGRES_HOST", None)
        os.environ.pop("POSTGRES_PORT", None)
        os.environ.pop("POSTGRES_DB", None)
        os.environ.pop("POSTGRES_USER", None)
        os.environ.pop("POSTGRES_PASSWORD", None)

        import app

        app_module = importlib.reload(app)

        self.assertEqual(app_module.DB_CONFIG["host"], "localhost")
        self.assertEqual(app_module.DB_CONFIG["port"], "5432")
        self.assertEqual(app_module.DB_CONFIG["database"], "quizdb")
        self.assertEqual(app_module.DB_CONFIG["user"], "quizuser")
        self.assertEqual(app_module.DB_CONFIG["password"], "quizpass")

    def test_falls_back_to_sqlite_when_postgres_auth_fails(self):
        os.environ["USE_SQLITE_FALLBACK"] = "true"
        import app

        app_module = importlib.reload(app)
        with patch.object(app_module.psycopg2, "connect", side_effect=app_module.psycopg2.OperationalError("boom")):
            conn = app_module.get_connection()
            self.assertIsInstance(conn, sqlite3.Connection)
            conn.close()

    def test_raises_when_postgres_unavailable_and_fallback_disabled(self):
        os.environ.pop("USE_SQLITE_FALLBACK", None)
        import app

        app_module = importlib.reload(app)
        with patch.object(app_module.psycopg2, "connect", side_effect=app_module.psycopg2.OperationalError("boom")):
            with self.assertRaises(app_module.DatabaseUnavailableError):
                app_module.get_connection()


if __name__ == "__main__":
    unittest.main()
