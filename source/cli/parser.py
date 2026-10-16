import argparse
import shlex

from colorama import Fore, Style

from commands.auth import cmd_Health, cmd_Logout, cmd_Me
from commands.events import cmd_EventsChains, cmd_EventsExport, cmd_EventsList, cmd_EventsTail
from commands.fs_packs import cmd_FsPackDelete, cmd_FsPackList, cmd_FsPackUpload
from commands.vm_images import cmd_VmImageDelete, cmd_VmImageList, cmd_VmImageUpload
from commands.trap_vm import cmd_TrapVm
from commands.personality_packs import cmd_PersonalityPackList
from commands.maintenance import cmd_DbReset, cmd_LogsClear
from commands.roles import (
	cmd_RoleCreate,
	cmd_RoleDelete,
	cmd_RoleList,
	cmd_RolePerms,
	cmd_RoleSetPerms,
)
from commands.users import (
	cmd_UserCreate,
	cmd_UserDisable,
	cmd_UserList,
	cmd_UserSetRole,
)
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
from commands.couriers import (
	cmd_CourierConfirm,
	cmd_CourierDeploy,
	cmd_CourierList,
	cmd_CourierPairList,
	cmd_CourierShow,
	cmd_TrapSetCourierSsh,
)
from commands.traps import (
	cmd_PairConfirm,
	cmd_PairList,
	cmd_TrapBind,
	cmd_TrapSetOwner,
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

	p_ul = sub.add_parser("user-list", help="список пользователей")
	p_ul.set_defaults(func=cmd_UserList)

	p_uc = sub.add_parser("user-create", help="создать пользователя")
	p_uc.add_argument("--username", required=True)
	p_uc.add_argument("--role-id", required=True)
	p_uc.add_argument("--password", default="", help="иначе спросит")
	p_uc.add_argument("--superadmin", action="store_true")
	p_uc.set_defaults(func=cmd_UserCreate)

	p_usr = sub.add_parser("user-set-role", help="сменить роль пользователя")
	p_usr.add_argument("user_id")
	p_usr.add_argument("--role-id", required=True)
	p_usr.set_defaults(func=cmd_UserSetRole)

	p_ud = sub.add_parser("user-disable", help="отключить или включить пользователя")
	p_ud.add_argument("user_id")
	p_ud.add_argument("--enable", action="store_true", help="включить обратно")
	p_ud.set_defaults(func=cmd_UserDisable)

	p_rl = sub.add_parser("role-list", help="список ролей")
	p_rl.set_defaults(func=cmd_RoleList)

	p_rp = sub.add_parser("role-perms", help="каталог прав")
	p_rp.set_defaults(func=cmd_RolePerms)

	p_rc = sub.add_parser("role-create", help="создать кастомную роль")
	p_rc.add_argument("--name", required=True)
	p_rc.add_argument("--permissions", default="", help="через запятую")
	p_rc.set_defaults(func=cmd_RoleCreate)

	p_rsp = sub.add_parser("role-set-perms", help="задать права роли")
	p_rsp.add_argument("role_id")
	p_rsp.add_argument("--permissions", required=True, help="через запятую")
	p_rsp.set_defaults(func=cmd_RoleSetPerms)

	p_rd = sub.add_parser("role-delete", help="удалить кастомную роль")
	p_rd.add_argument("role_id")
	p_rd.set_defaults(func=cmd_RoleDelete)

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
	p_pc.add_argument("--level", choices=["low", "medium", "high"], help="low=баннер, medium=вход/shell/http, high=VM")
	p_pc.add_argument("--port", type=int, help="порт сервиса")
	p_pc.add_argument(
		"--service",
		default="ssh",
		choices=["ssh", "http", "https", "tcp_banner", "postgres", "redis", "mysql", "container"],
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
	p_pc.add_argument("--image", default="", help="container: образ, например ghcr.io/org/honeypot:1.2.3")
	p_pc.add_argument("--container-port", dest="container_port", type=int, help="container: порт внутри контейнера")
	p_pc.add_argument("--image-token", dest="image_token", help="High: token образа vmi_...")
	p_pc.add_argument("--vm-name", dest="vm_name", default="hf-guest", help="High: имя VM")
	p_pc.add_argument("--snapshot", dest="snapshot", default="clean", help="High: snapshot")
	p_pc.add_argument("--rdp-port", dest="rdp_port", type=int, default=3389, help="High: RDP host port")
	p_pc.add_argument("--vm-cpus", dest="vm_cpus", type=int, default=2, help="High: CPU")
	p_pc.add_argument("--vm-memory-mb", dest="vm_memory_mb", type=int, default=4096, help="High: RAM MiB")
	p_pc.add_argument("--no-auto-start", dest="no_auto_start", action="store_true", help="High: не стартовать VM при bind")
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

	p_tvm = sub.add_parser("trap-vm", help="команда VirtualBox VM на ловушке")
	p_tvm.add_argument(
		"action",
		choices=["ensure", "start", "stop", "revert", "status"],
		help="vm_ensure|start|stop|revert|status",
	)
	p_tvm.add_argument("--trap-id", dest="trap_id", required=True, help="UUID ловушки")
	p_tvm.set_defaults(func=cmd_TrapVm)

	p_to = sub.add_parser("trap-set-owner", help="назначить владельца ловушки")
	p_to.add_argument("trap_id")
	p_to.add_argument("--user-id", dest="user_id", required=True, help="UUID пользователя")
	p_to.set_defaults(func=cmd_TrapSetOwner)

	p_tcs = sub.add_parser("trap-set-courier-ssh", help="SSH ловушки для визитов курьера")
	p_tcs.add_argument("trap_id")
	p_tcs.add_argument("--host", required=True)
	p_tcs.add_argument("--user", default="root")
	p_tcs.add_argument("--port", type=int, default=22)
	p_tcs.add_argument("--password", default="")
	p_tcs.add_argument("--private-key", dest="private_key", default=None)
	p_tcs.add_argument("--data-dir", dest="data_dir", default="/var/lib/metricsd")
	p_tcs.set_defaults(func=cmd_TrapSetCourierSsh)

	p_cl = sub.add_parser("courier-list", help="список курьеров")
	p_cl.set_defaults(func=cmd_CourierList)

	p_cs = sub.add_parser("courier-show", help="карточка курьера")
	p_cs.add_argument("courier_id")
	p_cs.set_defaults(func=cmd_CourierShow)

	p_cpl = sub.add_parser("courier-pair-list", help="входящие pairing курьеров")
	p_cpl.add_argument("--status", default="pending")
	p_cpl.set_defaults(func=cmd_CourierPairList)

	p_cc = sub.add_parser("courier-confirm", help="подтвердить pairing курьера")
	p_cc.add_argument("device_code")
	p_cc.add_argument("--name", default="courier")
	p_cc.set_defaults(func=cmd_CourierConfirm)

	p_cd = sub.add_parser("courier-deploy", help="поставить курьера на третий хост по SSH")
	p_cd.add_argument("--host", required=True)
	p_cd.add_argument("--user", default="root")
	p_cd.add_argument("--port", type=int, default=22)
	p_cd.add_argument("--api-base", default="")
	p_cd.add_argument("--password", default="")
	p_cd.set_defaults(func=cmd_CourierDeploy)

	p_el = sub.add_parser("events-list", help="список событий")
	p_el.add_argument("--trap-id", dest="trap_id", default=None)
	p_el.add_argument("--type", dest="type", default=None)
	p_el.add_argument("--source-ip", dest="source_ip", default=None)
	p_el.add_argument(
		"--min-priority",
		dest="min_priority",
		default=None,
		choices=["low", "medium", "high"],
		help="фильтр по приоритету (high/medium/low)",
	)
	p_el.add_argument("--limit", type=int, default=50)
	p_el.set_defaults(func=cmd_EventsList)

	p_ec = sub.add_parser("events-chains", help="цепочки source_ip по портам ловушки")
	p_ec.add_argument("--trap-id", dest="trap_id", default=None)
	p_ec.add_argument("--window-sec", dest="window_sec", type=int, default=3600)
	p_ec.set_defaults(func=cmd_EventsChains)

	p_ex = sub.add_parser("events-export", help="IoC-выгрузка CSV или STIX")
	p_ex.add_argument("--format", dest="format", default="csv", choices=["csv", "stix"])
	p_ex.add_argument("-o", "--output", dest="output", default="", help="файл (иначе stdout)")
	p_ex.add_argument("--trap-id", dest="trap_id", default=None)
	p_ex.add_argument("--type", dest="type", default=None)
	p_ex.add_argument("--source-ip", dest="source_ip", default=None)
	p_ex.add_argument(
		"--min-priority",
		dest="min_priority",
		default=None,
		choices=["low", "medium", "high"],
	)
	p_ex.add_argument("--since", dest="since", default=None, help="ISO дата начала")
	p_ex.add_argument("--until", dest="until", default=None, help="ISO дата конца")
	p_ex.add_argument("--limit", type=int, default=5000)
	p_ex.set_defaults(func=cmd_EventsExport)

	p_et = sub.add_parser("events-tail", help="SSE-лента событий (Ctrl+C стоп)")
	p_et.set_defaults(func=cmd_EventsTail)

	p_lc = sub.add_parser("logs-clear", help="удалить события и журнал аудита")
	p_lc.add_argument("--yes", action="store_true", help="без подтверждения")
	p_lc.set_defaults(func=cmd_LogsClear)

	p_dr = sub.add_parser("db-reset", help="очистить данные центра")
	p_dr.add_argument("--yes", action="store_true", help="без подтверждения")
	p_dr.set_defaults(func=cmd_DbReset)

	p_fpl = sub.add_parser("fs-pack-list", help="список пакетов файловой системы")
	p_fpl.set_defaults(func=cmd_FsPackList)

	p_fpu = sub.add_parser("fs-pack-upload", help="загрузить архив FS (.zip / .tar.gz)")
	p_fpu.add_argument("--file", required=True, help="путь к архиву")
	p_fpu.add_argument("--name", default="", help="имя пакета")
	p_fpu.set_defaults(func=cmd_FsPackUpload)

	p_fpd = sub.add_parser("fs-pack-delete", help="удалить пакет FS")
	p_fpd.add_argument("token", help="token пакета fsp_...")
	p_fpd.set_defaults(func=cmd_FsPackDelete)

	p_vil = sub.add_parser("vm-image-list", help="список образов VM (OVA)")
	p_vil.set_defaults(func=cmd_VmImageList)

	p_viu = sub.add_parser("vm-image-upload", help="загрузить OVA в реестр центра")
	p_viu.add_argument("--file", required=True, help="путь к .ova / .vdi / .vmdk")
	p_viu.add_argument("--name", default="", help="имя образа")
	p_viu.set_defaults(func=cmd_VmImageUpload)

	p_vid = sub.add_parser("vm-image-delete", help="удалить образ VM")
	p_vid.add_argument("token", help="token образа vmi_...")
	p_vid.set_defaults(func=cmd_VmImageDelete)

	p_ppl = sub.add_parser("personality-pack-list", help="список personality packs")
	p_ppl.set_defaults(func=cmd_PersonalityPackList)

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
