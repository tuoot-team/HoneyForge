from __future__ import annotations

import getpass
import os
import select
import sys

try:
	import termios
	import tty
except ImportError:  # pragma: no cover - не Linux
	termios = None
	tty = None


# Стрелка приходит как Esc и сразу продолжение. Если за это время байтов нет - это одиночный Esc.
_ESC_FOLLOW_SEC = 0.05


class LineGoBack(Exception):
	"""Одиночный Esc: вернуть предыдущий ввод."""


class AnswerStack:
	"""Ответы мастера. Ключ побочного действия - ответы на момент вызова."""

	def __init__(self) -> None:
		self.answers: list[tuple[str, bool]] = []
		self.text_history: list[str] = []
		self.effects: dict[str, list[tuple[tuple[str, ...], object]]] = {}
		self.replay_index = 0
		self.replay_limit = 0
		self.replaying = False
		self.edit_prefill: str | None = None
		self.events_tail_opened = False

	def reset(self) -> None:
		self.answers.clear()
		self.text_history.clear()
		self.effects.clear()
		self.replay_index = 0
		self.replay_limit = 0
		self.replaying = False
		self.edit_prefill = None
		self.events_tail_opened = False

	def commit(self, raw: str, *, secret: bool) -> None:
		self.answers.append((raw, secret))
		if secret or not raw:
			return
		self.text_history.append(raw)

	def prepare_Replay(self) -> None:
		if not self.answers:
			self.replaying = False
			self.edit_prefill = None
			return
		raw, secret = self.answers.pop()
		self.edit_prefill = raw
		self.replaying = True
		self.replay_index = 0
		self.replay_limit = len(self.answers)
		if not secret and self.text_history and self.text_history[-1] == raw:
			self.text_history.pop()

	def take_Replay(self) -> tuple[str, bool] | None:
		if not self.replaying or self.replay_index >= self.replay_limit:
			return None
		item = self.answers[self.replay_index]
		self.replay_index += 1
		return item

	def take_Prefill(self) -> str | None:
		if self.replaying and self.replay_index < self.replay_limit:
			return None
		if self.edit_prefill is None:
			self.replaying = False
			return None
		value = self.edit_prefill
		self.edit_prefill = None
		self.replaying = False
		return value

	def run_Once(self, key: str, call):
		snapshot = tuple(item[0] for item in self.answers)
		for found_snapshot, value in self.effects.get(key, []):
			if found_snapshot == snapshot:
				return value
		value = call()
		self.effects.setdefault(key, []).append((snapshot, value))
		return value


class _LineBuffer:
	def __init__(self, prefill: str, history: list[str] | None) -> None:
		self.chars = list(prefill)
		self.cursor = len(self.chars)
		self.history = list(history or [])
		self.history_index = len(self.history)
		self.draft = prefill

	def text(self) -> str:
		return "".join(self.chars)

	def shown(self, echo: bool) -> str:
		text = self.text()
		if echo:
			return text
		return "*" * len(text)

	def move_Left(self) -> None:
		if self.cursor > 0:
			self.cursor -= 1

	def move_Right(self) -> None:
		if self.cursor < len(self.chars):
			self.cursor += 1

	def move_Home(self) -> None:
		self.cursor = 0

	def move_End(self) -> None:
		self.cursor = len(self.chars)

	def backspace(self) -> None:
		if self.cursor <= 0:
			return
		self.cursor -= 1
		del self.chars[self.cursor]

	def delete(self) -> None:
		if self.cursor < len(self.chars):
			del self.chars[self.cursor]

	def insert(self, text: str) -> None:
		for char in text:
			self.chars.insert(self.cursor, char)
			self.cursor += 1

	def history_Up(self) -> None:
		if not self.history or self.history_index <= 0:
			return
		if self.history_index == len(self.history):
			self.draft = self.text()
		self.history_index -= 1
		self._load(self.history[self.history_index])

	def history_Down(self) -> None:
		if self.history_index >= len(self.history):
			return
		self.history_index += 1
		if self.history_index == len(self.history):
			self._load(self.draft)
		else:
			self._load(self.history[self.history_index])

	def _load(self, text: str) -> None:
		self.chars = list(text)
		self.cursor = len(self.chars)


def _read_Fallback(prompt: str, *, echo: bool) -> str:
	if not echo:
		return getpass.getpass(prompt)
	return input(prompt)


def _is_TTY() -> bool:
	if termios is None or tty is None:
		return False
	try:
		return sys.stdin.isatty() and sys.stdout.isatty()
	except ValueError:
		return False


def _utf8_Length(first: int) -> int:
	if first & 0x80 == 0:
		return 1
	if first & 0xE0 == 0xC0:
		return 2
	if first & 0xF0 == 0xE0:
		return 3
	if first & 0xF8 == 0xF0:
		return 4
	return 1


def _read_Byte(fd: int, timeout: float | None) -> bytes | None:
	if timeout is not None:
		ready, _, _ = select.select([fd], [], [], timeout)
		if not ready:
			return None
	data = os.read(fd, 1)
	if not data:
		return b""
	return data


def _read_Escape(fd: int) -> str | None:
	"""None - одиночный Esc. Иначе тело последовательности после [ или O."""
	first = _read_Byte(fd, _ESC_FOLLOW_SEC)
	if first is None or first == b"":
		return None
	if first not in (b"[", b"O"):
		return ""
	body = ""
	while len(body) < 16:
		nxt = _read_Byte(fd, _ESC_FOLLOW_SEC)
		if nxt is None or nxt == b"":
			break
		char = nxt.decode("latin1")
		body += char
		if char.isalpha() or char == "~":
			break
	return body


def _map_Escape(body: str) -> str | None:
	if not body:
		return None
	if body in ("3~",):
		return "delete"
	if body in ("1~", "7~", "H"):
		return "home"
	if body in ("4~", "8~", "F"):
		return "end"
	last = body[-1]
	if last == "A":
		return "up"
	if last == "B":
		return "down"
	if last == "C":
		return "right"
	if last == "D":
		return "left"
	if last == "H":
		return "home"
	if last == "F":
		return "end"
	return None


def _read_Key(fd: int) -> tuple[str, str]:
	raw = _read_Byte(fd, None)
	if raw is None or raw == b"":
		return ("eof", "")
	if raw == b"\x1b":
		body = _read_Escape(fd)
		if body is None:
			return ("esc", "")
		mapped = _map_Escape(body)
		if mapped is None:
			return ("ignore", "")
		return ("key", mapped)
	if raw in (b"\r", b"\n"):
		return ("enter", "")
	if raw in (b"\x7f", b"\x08"):
		return ("key", "backspace")
	if raw == b"\x03":
		return ("intr", "")
	if raw == b"\x04":
		return ("eof", "")
	if raw == b"\x01":
		return ("key", "home")
	if raw == b"\x05":
		return ("key", "end")
	needed = _utf8_Length(raw[0]) - 1
	buf = raw
	for _ in range(needed):
		more = _read_Byte(fd, _ESC_FOLLOW_SEC)
		if not more:
			return ("ignore", "")
		buf += more
	try:
		text = buf.decode("utf-8")
	except UnicodeDecodeError:
		return ("ignore", "")
	if text.isprintable():
		return ("char", text)
	return ("ignore", "")


def _redraw(prompt: str, shown: str, cursor: int) -> None:
	sys.stdout.write("\r\x1b[2K")
	sys.stdout.write(prompt)
	sys.stdout.write(shown)
	tail = len(shown) - cursor
	if tail > 0:
		sys.stdout.write(f"\x1b[{tail}D")
	sys.stdout.flush()


def _finish_Line() -> None:
	sys.stdout.write("\r\n")
	sys.stdout.flush()


def _apply_Key(buf: _LineBuffer, kind: str, value: str) -> None:
	if kind == "char":
		buf.insert(value)
		return
	if value == "left":
		buf.move_Left()
	elif value == "right":
		buf.move_Right()
	elif value == "up":
		buf.history_Up()
	elif value == "down":
		buf.history_Down()
	elif value == "home":
		buf.move_Home()
	elif value == "end":
		buf.move_End()
	elif value == "backspace":
		buf.backspace()
	elif value == "delete":
		buf.delete()


def _edit_Loop(
	fd: int,
	prompt: str,
	*,
	history: list[str] | None,
	prefill: str,
	echo: bool,
	allow_back: bool,
) -> str:
	buf = _LineBuffer(prefill, history)
	while True:
		_redraw(prompt, buf.shown(echo), buf.cursor)
		kind, value = _read_Key(fd)
		if kind == "enter":
			_finish_Line()
			return buf.text()
		if kind == "esc":
			if allow_back:
				_finish_Line()
				raise LineGoBack
			continue
		if kind == "intr":
			_finish_Line()
			raise KeyboardInterrupt
		if kind == "eof":
			if not buf.chars:
				_finish_Line()
				raise EOFError
			continue
		if kind == "key":
			_apply_Key(buf, kind, value)
		elif kind == "char":
			_apply_Key(buf, kind, value)


def read_Line(
	prompt: str,
	*,
	history: list[str] | None = None,
	prefill: str = "",
	echo: bool = True,
	allow_back: bool = False,
) -> str:
	"""Строка с терминала. Вне TTY - обычный input или getpass."""
	if not _is_TTY():
		return _read_Fallback(prompt, echo=echo)
	fd = sys.stdin.fileno()
	old = termios.tcgetattr(fd)
	try:
		tty.setraw(fd)
		return _edit_Loop(
			fd,
			prompt,
			history=history,
			prefill=prefill,
			echo=echo,
			allow_back=allow_back,
		)
	finally:
		termios.tcsetattr(fd, termios.TCSADRAIN, old)
