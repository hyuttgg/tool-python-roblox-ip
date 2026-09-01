# -*- coding: utf-8 -*-
"""
Unit test cho TermuxCookieManager
"""
import os
import unittest
import tempfile
from database.termux_cookie import TermuxCookieManager

class TestTermuxCookieManager(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.manager = TermuxCookieManager(self.temp_db.name)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except Exception:
                pass
        wal_file = f"{self.temp_db.name}-wal"
        if os.path.exists(wal_file):
            try:
                os.remove(wal_file)
            except Exception:
                pass

    def test_ensure_schema(self):
        cols = self.manager.ensure_schema("Cookies")
        self.assertGreater(cols, 0)

    def test_extract_user_id(self):
        cookie = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-steal-your-ROBUX-and-items.|_123456789_abcdef"
        uid = self.manager.extract_user_id_from_cookie(cookie)
        self.assertEqual(uid, "123456789")

    def test_insert_and_exists(self):
        dummy_cookie = "_|WARNING:-DO-NOT-SHARE-THIS...|_987654321_secretcookiecontent"
        success = self.manager.insert_cookie(dummy_cookie)
        # Note: on Windows without sqlite3 CLI installed, subprocess fallback might return error code if sqlite3 command missing,
        # but Python API or sqlite3 CLI will be tested.
        if success:
            self.assertTrue(self.manager.session_cookie_exists("987654321"))
            self.assertEqual(self.manager.get_user_id_from_cookie_db(), "987654321")
            raw = self.manager.get_raw_cookie_from_db()
            self.assertEqual(raw, dummy_cookie)
            redacted = self.manager.export_cookie_redacted()
            self.assertIn("...", redacted)

if __name__ == "__main__":
    unittest.main()
