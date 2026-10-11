from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agent import texts

BUFFER_FILE = Path(__file__).resolve().parents[1] / "events_buffer.db"

class EventBuffer:

	def __init__(self, path: Path = BUFFER_FILE, debug: bool = False):
		self.path = path
		self.debug = debug
		self.conn = sqlite3.connect(str(path), check_same_thread=False)
		self.conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS events (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				payload TEXT NOT NULL,
				sent INTEGER NOT NULL DEFAULT 0,
				created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
			)
			"""
		)
		self.conn.execute(
			"CREATE INDEX IF NOT EXISTS idx_events_sent ON events (sent, id)"
		)
		self.conn.commit()

	def close(self) -> None:
		self.conn.close()

	def debug_Log(self, message: str) -> None:
		if self.debug:
			print(f"[DEBUG] {message}")

	def add(self, event: dict[str, Any]) -> None:
		self.conn.execute(
			"INSERT INTO events (payload) VALUES (?)",
			(json.dumps(event, ensure_ascii=False),),
		)
		self.conn.commit()
		self.debug_Log(texts.MSG_BUFFER_ADDED.format(
			event_type=event.get("event_type", "?")
		))

	def pending(self, limit: int = 200) -> list[tuple[int, dict]]:
		cur = self.conn.execute(
			"SELECT id, payload FROM events WHERE sent = 0 ORDER BY id LIMIT ?",
			(limit,),
		)
		return [(row[0], json.loads(row[1])) for row in cur.fetchall()]

	def mark_Sent(self, ids: list[int]) -> None:
		if not ids:
			return
		placeholders = ",".join("?" * len(ids))
		self.conn.execute(
			f"UPDATE events SET sent = 1 WHERE id IN ({placeholders})",
			ids,
		)
		self.conn.commit()
		self.debug_Log(texts.MSG_BUFFER_SENT.format(count=len(ids)))

	def count_Pending(self) -> int:
		cur = self.conn.execute("SELECT COUNT(*) FROM events WHERE sent = 0")
		return cur.fetchone()[0]
