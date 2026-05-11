import sqlite3
import threading
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            contact_channel TEXT NOT NULL,
            contact_value TEXT NOT NULL,
            request_text TEXT NOT NULL,
            priority TEXT NOT NULL,
            qualified INTEGER NOT NULL,
            ai_summary TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL,
            target TEXT NOT NULL,
            body TEXT NOT NULL,
            context_type TEXT NOT NULL,
            context_id INTEGER,
            sent_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            text_back_sent_at TEXT
        );

        CREATE TABLE IF NOT EXISTS estimates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            follow_up_at TEXT NOT NULL,
            follow_up_sent_at TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS technicians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            skills TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            available INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            required_skill TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            status TEXT NOT NULL,
            technician_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (technician_id) REFERENCES technicians (id)
        );

        CREATE TABLE IF NOT EXISTS maintenance_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            asset_name TEXT NOT NULL,
            next_service_date TEXT NOT NULL,
            interval_days INTEGER NOT NULL,
            last_reminder_at TEXT
        );

        CREATE TABLE IF NOT EXISTS solar_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            system_kw REAL NOT NULL,
            status TEXT NOT NULL,
            doc_packet_id INTEGER,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            service_type TEXT NOT NULL,
            labor_hours REAL NOT NULL,
            materials_cost REAL NOT NULL,
            total REAL NOT NULL,
            notes TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(schema)
                conn.commit()
                self._seed_technicians(conn)
            finally:
                conn.close()

    def _seed_technicians(self, conn: sqlite3.Connection) -> None:
        existing = conn.execute("SELECT COUNT(*) as count FROM technicians").fetchone()
        if existing and existing["count"] > 0:
            return
        seed_rows = [
            ("Ava Sparks", "service,breaker,panel", 39.9612, -82.9988, 1),
            ("Noah Voltage", "solar,service", 41.4993, -81.6944, 1),
            ("Mia Conduit", "permit,panel,inspection", 39.1031, -84.5120, 1),
        ]
        conn.executemany(
            """
            INSERT INTO technicians(name, skills, latitude, longitude, available)
            VALUES (?, ?, ?, ?, ?)
            """,
            seed_rows,
        )
        conn.commit()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(sql, params)
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()

    def query_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(sql, params).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

    def query_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(sql, params).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()
