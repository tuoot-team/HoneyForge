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
	cmd_ProfileUpdate,
)
from commands.deploy import cmd_Deploy
from commands.setup import cmd_Guide, cmd_Setup
from commands.traps import (
	cmd_PairConfirm,
	cmd_PairList,
	cmd_TrapBind,
	cmd_TrapShow,
	cmd_TrapsList,
)
from texts import HelpText, clear_Screen, print_Logo


def create_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(prog="forge", add_help=False)
	sub = parser.add_subparsers(dest="command", required=True)

	p_help = sub.add_parser("help", help="справка")
	p_help.set_defaults(func=lambda _a: print(HelpText))

	p_clear = sub.add_parser("clear", help="очистить экран")
	p_clear.set_defaults(func=lambda _a: clear_Screen())

	p_logo = sub.add_parser("logo", help="показать логотип")
	p_logo.set_defaults(func=lambda _a: print_Logo())

	p_setup = sub.add_parser("setup", help="пошаговый гайд: профиль → pairing → события")
	p_setup.set_defaults(func=cmd_Setup)

	p_guide = sub.add_parser("guide", help="алиас setup")
	p_guide.set_defaults(func=cmd_Guide)

	p_deploy = sub.add_parser("deploy", help="поставить агент на хост по SSH")
	p_deploy.add_argument("--host", default="", help="IP хоста ловушки")
	p_deploy.add_argument("--user", default="root", help="логин SSH")
	p_deploy.add_argument("--port", type=int, default=22, help="порт SSH")
	p_deploy.add_argument("--api-base", default="", help="адрес центра, видимый с хоста")
	p_deploy.add_argument("--password", default="", help="пароль SSH, иначе спросит")
	p_deploy.set_defaults(func=cmd_Deploy)

	p_health = sub.add_parser("health", help="проверка API /health")
	p_health.set_defaults(func=cmd_Health)

	p_me = sub.add_parser("me", help="текущий оператор")
	p_me.set_defaults(func=cmd_Me)

	p_logout = sub.add_parser("logout", help="сбросить Bearer-токен")
	p_logout.set_defaults(func=cmd_Logout)

	p_ps = sub.add_parser("profile-schema", help="схема конструктора")
	p_ps.set_defaults(func=cmd_ProfileSchema)

	p_pl = sub.add_parser("profile-list", help="список профилей")
	p_pl.set_defaults(func=cmd_ProfileList)

	p_pshow = sub.add_parser("profile-show", help="показать профиль")
	p_pshow.add_argument("profile_id")
	p_pshow.set_defaults(func=cmd_ProfileShow)

	p_pc = sub.add_parser("profile-create", help="создать профиль из слотов сервиса")
	p_pc.add_argument("--file", help="JSON-файл тела ProfileCreate")
	p_pc.add_argument("--name", help="имя (если без --file)")
	p_pc.add_argument("--level", choices=["low", "medium", "high"], help="low=баннер, medium=вход/shell/http")
	p_pc.add_argument("--port", type=int, help="порт сервиса")
	p_pc.add_argument(
		"--service",
		default="ssh",
		choices=["ssh", "http", "https", "tcp_banner", "postgres", "redis", "mysql"],
		help="тип сервиса (default ssh)",
	)
	p_pc.add_argument(
		"--services",
		help="несколько ловушек через запятую, порты стандартные",
	)
	p_pc.add_argument(
		"--auth",
		choices=["off", "allow_all", "allow_listed", "second_attempt_sticky"],
		help="режим модуля auth",
	)
	p_pc.add_argument("--username", help="логин приманки")
	p_pc.add_argument("--password", help="пароль приманки")
	p_pc.add_argument("--banner", help="баннер SSH/TCP или версия HTTP, если нет --server")
	p_pc.add_argument("--server", help="HTTP-заголовок Server, например nginx/1.24.0")
	p_pc.add_argument("--auth-path", dest="auth_path", help="путь HTTP auth (default /admin)")
	p_pc.add_argument("--delay-min", dest="delay_min", type=int, help="мин. задержка входа, мс")
	p_pc.add_argument("--delay-max", dest="delay_max", type=int, help="макс. задержка входа, мс")
	p_pc.add_argument("--sticky-ttl", dest="sticky_ttl", type=int, help="TTL привязки IP, часы")
	p_pc.add_argument("--no-shell", dest="no_shell", action="store_true", help="SSH: вход без shell")
	p_pc.add_argument("--description", default="", help="описание")
	p_pc.set_defaults(func=cmd_ProfileCreate)

	p_pu = sub.add_parser("profile-update", help="обновить профиль (JSON или имя/описание)")
	p_pu.add_argument("profile_id")
	p_pu.add_argument("--file", help="JSON ProfileCreate: name, level, blocks")
	p_pu.add_argument("--name", help="новое имя")
	p_pu.add_argument("--description", help="новое описание")
	p_pu.set_defaults(func=cmd_ProfileUpdate)

	p_pd = sub.add_parser("profile-delete", help="удалить профиль")
	p_pd.add_argument("profile_id")
	p_pd.set_defaults(func=cmd_ProfileDelete)

	p_plist = sub.add_parser("pair-list", help="входящие запросы pairing")
	p_plist.add_argument(
		"--status",
		default="pending",
		choices=["pending", "confirmed", "completed", "expired", "all"],
		help="фильтр статуса (default pending)",
	)
	p_plist.set_defaults(func=cmd_PairList)

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
