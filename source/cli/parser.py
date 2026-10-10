import argparse
import shlex

from colorama import Fore, Style

from commands.auth import cmd_Health, cmd_Logout, cmd_Me
from commands.events import cmd_EventsList, cmd_EventsTail
from commands.profiles import (
	cmd_ProfileCreate,
	cmd_ProfileDelete,
	cmd_ProfileList,
	cmd_ProfileSchema,
	cmd_ProfileShow,
)
from commands.traps import cmd_PairConfirm, cmd_TrapBind, cmd_TrapShow, cmd_TrapsList
from texts import HelpText, clear_Screen


def create_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(prog="forge", add_help=False)
	sub = parser.add_subparsers(dest="command", required=True)

	# служебные
	p_help = sub.add_parser("help", help="справка")
	p_help.set_defaults(func=lambda _a: print(HelpText))

	p_clear = sub.add_parser("clear", help="очистить экран")
	p_clear.set_defaults(func=lambda _a: clear_Screen())

	p_health = sub.add_parser("health", help="проверка API /health")
	p_health.set_defaults(func=cmd_Health)

	p_me = sub.add_parser("me", help="текущий оператор")
	p_me.set_defaults(func=cmd_Me)

	p_logout = sub.add_parser("logout", help="сбросить Bearer-токен")
	p_logout.set_defaults(func=cmd_Logout)

	# profiles
	p_ps = sub.add_parser("profile-schema", help="схема конструктора")
	p_ps.set_defaults(func=cmd_ProfileSchema)

	p_pl = sub.add_parser("profile-list", help="список профилей")
	p_pl.set_defaults(func=cmd_ProfileList)

	p_pshow = sub.add_parser("profile-show", help="показать профиль")
	p_pshow.add_argument("profile_id")
	p_pshow.set_defaults(func=cmd_ProfileShow)

	p_pc = sub.add_parser("profile-create", help="создать профиль")
	p_pc.add_argument("--file", help="JSON-файл тела ProfileCreate")
	p_pc.add_argument("--name", help="имя (если без --file)")
	p_pc.add_argument("--level", choices=["low", "medium", "high"], help="уровень")
	p_pc.add_argument("--port", type=int, help="порт сервиса")
	p_pc.add_argument("--service", default="ssh", help="имя сервиса (default ssh)")
	p_pc.add_argument("--description", default="", help="описание")
	p_pc.set_defaults(func=cmd_ProfileCreate)

	p_pd = sub.add_parser("profile-delete", help="удалить профиль")
	p_pd.add_argument("profile_id")
	p_pd.set_defaults(func=cmd_ProfileDelete)

	# pairing / traps
	p_pair = sub.add_parser("pair-confirm", help="подтвердить device_code агента")
	p_pair.add_argument("device_code")
	p_pair.add_argument("--name", default="trap", help="имя ловушки")
	p_pair.add_argument("--profile-id", dest="profile_id", default=None)
	p_pair.set_defaults(func=cmd_PairConfirm)

	p_tl = sub.add_parser("traps-list", help="список ловушек")
	p_tl.set_defaults(func=cmd_TrapsList)

	p_ts = sub.add_parser("trap-show", help="статус ловушки")
	p_ts.add_argument("trap_id")
	p_ts.set_defaults(func=cmd_TrapShow)

	p_tb = sub.add_parser("trap-bind", help="привязать профиль к ловушке")
	p_tb.add_argument("trap_id")
	p_tb.add_argument("profile_id")
	p_tb.set_defaults(func=cmd_TrapBind)

	# events
	p_el = sub.add_parser("events-list", help="список событий")
	p_el.add_argument("--trap-id", dest="trap_id", default=None)
	p_el.add_argument("--type", dest="type", default=None)
	p_el.add_argument("--source-ip", dest="source_ip", default=None)
	p_el.add_argument("--limit", type=int, default=50)
	p_el.set_defaults(func=cmd_EventsList)

	p_et = sub.add_parser("events-tail", help="SSE-лента событий (Ctrl+C стоп)")
	p_et.set_defaults(func=cmd_EventsTail)

	return parser


def execute_args(parser: argparse.ArgumentParser, input_args: str) -> None:
	line = input_args.strip()
	if not line:
		return
	args_list = shlex.split(line)
	try:
		parsed = parser.parse_args(args_list)
	except SystemExit:
		# argparse печатает usage сам; не роняем REPL
		raise
	if not hasattr(parsed, "func"):
		print(Fore.YELLOW + HelpText + Style.RESET_ALL)
		return
	parsed.func(parsed)
