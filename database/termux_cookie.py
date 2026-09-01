# -*- coding: utf-8 -*-
"""
Termux / Android SQLite Cookie Patch Module
Khắc phục triệt để các lỗi trên Termux / VSPhone / Delta / Cloud Phone:
- Override .sqliterc 'box mode' bằng '-cmd .mode list -cmd .headers off'
- Tự động checkpoint WAL (merge WAL vào main DB) trước khi query
- Tạo lại schema bảng nếu bị rỗng (0 cột)
- Quản lý & xác minh Insert Cookie, Session Status, Cookie Redacting, User ID Extraction
"""

import os
import re
import sqlite3
import shutil
import subprocess
from typing import Optional, Tuple
from config.logging import setup_logger

logger = setup_logger("termux_cookie")

DEFAULT_COOKIE_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS Cookies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    cookie_value TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

class TermuxCookieManager:
    def __init__(self, db_path: str):
        self.db_path = str(db_path)

    def _sqlite_query(self, query: str, db_path: Optional[str] = None) -> Tuple[int, str, str]:
        """
        Chạy sqlite3 CLI với ép cờ -cmd '.mode list' -cmd '.headers off'
        để đè hoàn toàn file .sqliterc (Box Mode -> List Mode).
        Nếu không có CLI 'sqlite3', tự động dùng module sqlite3 của Python để xử lý tương thích.
        """
        target_db = db_path or self.db_path

        # Ưu tiên dùng CLI sqlite3 nếu có sẵn trên hệ thống (ví dụ Termux)
        if shutil.which("sqlite3"):
            cmd = [
                "sqlite3",
                "-cmd", ".mode list",
                "-cmd", ".headers off",
                target_db,
                query
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return res.returncode, res.stdout.strip(), res.stderr.strip()
            except Exception as e:
                logger.warning(f"_sqlite_query CLI exception ({e}), falling back to Python sqlite3 driver...")

        # Fallback bằng Python sqlite3 driver (List mode format)
        try:
            conn = sqlite3.connect(target_db, timeout=10.0)
            cursor = conn.cursor()
            
            # Xử lý nhiều câu lệnh nếu có dấu ;
            statements = [s.strip() for s in query.split(";") if s.strip()]
            output_lines = []
            for stmt in statements:
                cursor.execute(stmt)
                if cursor.description:
                    rows = cursor.fetchall()
                    for row in rows:
                        line = "|".join("" if col is None else str(col) for col in row)
                        output_lines.append(line)
            conn.commit()
            conn.close()
            return 0, "\n".join(output_lines), ""
        except Exception as py_err:
            logger.error(f"_sqlite_query python fallback error: {py_err}")
            return -1, "", str(py_err)

    def _checkpoint_wal(self, db_path: Optional[str] = None) -> bool:
        """
        Gộp (merge) file WAL vào DB chính TRƯỚC khi đọc/ghi để không làm mất dữ liệu.
        Không xoá file '-wal', dùng PRAGMA wal_checkpoint(FULL/RESTART).
        """
        target_db = db_path or self.db_path
        wal_file = f"{target_db}-wal"
        if not os.path.exists(wal_file):
            return True

        code, out, err = self._sqlite_query("PRAGMA wal_checkpoint(FULL);", target_db)
        if code == 0:
            logger.info(f"WAL Checkpoint SUCCESS: {out}")
            return True
        else:
            logger.warning(f"WAL Checkpoint warning ({err}), trying RESTART...")
            code2, out2, err2 = self._sqlite_query("PRAGMA wal_checkpoint(RESTART);", target_db)
            return code2 == 0

    def ensure_schema(self, table_name: str = "Cookies") -> int:
        """
        Kiểm tra số cột trong schema. Nếu rỗng (0 cột) hoặc chưa có bảng,
        tiến hành tự động CREATE TABLE fallback.
        """
        self._checkpoint_wal()
        query = f"PRAGMA table_info({table_name});"
        code, out, err = self._sqlite_query(query)
        
        columns = [line.split("|")[1] for line in out.splitlines() if "|" in line]
        if not columns or len(columns) == 0:
            logger.warning(f"Schema rỗng (0 cột) cho bảng {table_name}. Đang tạo lại schema mặc định...")
            code_crt, _, err_crt = self._sqlite_query(DEFAULT_COOKIE_TABLE_SCHEMA)
            if code_crt != 0:
                logger.error(f"Khởi tạo schema thất bại: {err_crt}")
                return 0
            # Kiểm tra lại schema
            code, out, err = self._sqlite_query(query)
            columns = [line.split("|")[1] for line in out.splitlines() if "|" in line]

        col_count = len(columns)
        logger.info(f"-> DB schema: {col_count} cot")
        return col_count

    def session_cookie_exists(self, user_id: Optional[str] = None) -> bool:
        """
        Kiểm tra sự tồn tại của session cookie trong DB.
        Ép list mode đè .sqliterc để không bị lỗi parse từ Box Mode.
        """
        self._checkpoint_wal()
        self.ensure_schema("Cookies")
        
        if user_id:
            query = f"SELECT COUNT(*) FROM Cookies WHERE user_id = '{user_id}' AND status = 'ACTIVE';"
        else:
            query = "SELECT COUNT(*) FROM Cookies WHERE status = 'ACTIVE' AND cookie_value IS NOT NULL AND length(cookie_value) > 10;"

        code, out, err = self._sqlite_query(query)
        if code != 0:
            logger.error(f"session_cookie_exists query error: {err}")
            return False

        try:
            clean_out = re.sub(r"[^\d]", "", out)
            count = int(clean_out) if clean_out else 0
            return count > 0
        except ValueError as e:
            logger.error(f"session_cookie_exists parse error '{out}': {e}")
            return False

    def insert_cookie(self, cookie_value: str, user_id: Optional[str] = None) -> bool:
        """
        Chèn cookie mới vào database với xác minh (verify count) đầy đủ.
        """
        if not cookie_value or not cookie_value.strip():
            logger.error("Cookie rỗng, hủy chèn!")
            return False

        cookie_value = cookie_value.strip()
        if not user_id:
            user_id = self.extract_user_id_from_cookie(cookie_value) or "UNKNOWN"

        self.ensure_schema("Cookies")
        
        safe_cookie = cookie_value.replace("'", "''")
        safe_uid = user_id.replace("'", "''")

        insert_sql = f"""
        INSERT INTO Cookies (user_id, cookie_value, status, updated_at) 
        VALUES ('{safe_uid}', '{safe_cookie}', 'ACTIVE', CURRENT_TIMESTAMP);
        """
        code, out, err = self._sqlite_query(insert_sql)
        if code != 0:
            logger.error(f"FAIL: Cookie khong duoc chen ({err})")
            return False

        # Thực hiện checkpoint WAL sau khi insert thay vì rm -wal
        self._checkpoint_wal()

        # Verify insertion
        verify_sql = f"SELECT COUNT(*) FROM Cookies WHERE user_id = '{safe_uid}' AND cookie_value = '{safe_cookie}';"
        v_code, v_out, _ = self._sqlite_query(verify_sql)
        clean_out = re.sub(r"[^\d]", "", v_out)
        verified_rows = int(clean_out) if clean_out else 0

        if verified_rows > 0:
            logger.info(f"Chen cookie xong ... (verified: {verified_rows} row)")
            return True
        else:
            logger.error("FAIL: Cookie khong duoc chen (verify count = 0)")
            return False

    def extract_user_id_from_cookie(self, cookie_value: str) -> Optional[str]:
        """
        Bóc tách User ID từ Cookie Roblox (.ROBLOSECURITY).
        """
        if not cookie_value:
            return None
        match = re.search(r"_([0-9]{5,15})_", cookie_value)
        if match:
            return match.group(1)
        match_alt = re.search(r"(\d{6,15})", cookie_value)
        if match_alt:
            return match_alt.group(1)
        return None

    def get_user_id_from_cookie_db(self) -> Optional[str]:
        """
        Đọc User ID từ Cookie mới nhất trong DB.
        """
        self._checkpoint_wal()
        query = "SELECT user_id FROM Cookies WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1;"
        code, out, err = self._sqlite_query(query)
        if code == 0 and out:
            lines = [line.strip() for line in out.splitlines() if line.strip() and not line.startswith("┌") and not line.startswith("│")]
            return lines[0] if lines else None
        return None

    def get_raw_cookie_from_db(self) -> Optional[str]:
        """
        Đọc Raw Cookie chưa mã hóa từ DB.
        """
        self._checkpoint_wal()
        query = "SELECT cookie_value FROM Cookies WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1;"
        code, out, err = self._sqlite_query(query)
        if code == 0 and out:
            lines = [line.strip() for line in out.splitlines() if line.strip() and not line.startswith("┌") and not line.startswith("│")]
            return lines[0] if lines else None
        return None

    def export_cookie_redacted(self) -> str:
        """
        Xuất Cookie đã che thông tin nhạy cảm (redacted) để in log an toàn.
        """
        raw = self.get_raw_cookie_from_db()
        if not raw:
            return "NO_COOKIE"
        if len(raw) <= 30:
            return raw[:5] + "..." + raw[-5:]
        return raw[:15] + "..." + raw[-15:]
