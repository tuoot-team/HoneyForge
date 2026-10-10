import os

from colorama import Fore, Style


def print_Logo():
	print(Fore.MAGENTA + r"""
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠰⣾⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⣴⡏⠀⠀⢀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⣷⣄⠀⠀⠀⠀⢀⣼⣿⣁⣤⡶⠁⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢀⣀⣤⣶⣿⣿⣿⣿⣿⡄⠀⢠⣷⣾⣿⣿⣿⣿⣁⣀⡀⠀⠀
⠀⠀⠀⢀⣠⣴⣾⡿⠟⠋⠉⠀⠈⢿⣿⣿⠷⠀⣾⠿⠛⣿⣿⠿⠛⠋⠁⠀⠀⠀
⠀⢲⣿⡿⠟⠋⠁⠀⠀⠀⠀⢀⣀⣈⣁⣀⣀⣀⣀⣀⣀⣁⣀⣀⣀⡀⠀⠀⠀⠀
⠀⠈⠁⠀⠀⠀⢠⣤⣤⣤⣤⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠙⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠄⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠋⠁⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⠛⠛⢛⣿⣿⣿⣿⣿⣿⡟⠛⠛⠛⠃⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⣿⣿⣿⣿⣿⣿⣿⣆⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣄⣀⡀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠁⠀⠀⠀
	""" + Style.RESET_ALL)


def clear_Screen():
	os.system("cls" if os.name == "nt" else "clear")


PasswordErrorText = "Неверный пароль. Попробуйте ещё раз."

LoginSuccessText = "Вход выполнен. Добро пожаловать в HoneyForge."

WelcomeText = "Введите help - список команд."

LogoutSuccessText = "Токен сброшен (logout)."

MeErrorText = "me: {detail}"

MsgApiError = "API: {detail}"

ProfileCreatedText = "Профиль создан: {profile_id}"

ProfileDeletedText = "Профиль удалён: {profile_id}"

PairConfirmText = "Pairing подтверждён."

TrapBoundText = "Профиль привязан к ловушке."

EventsTailHintText = "Слушаю SSE /api/v1/events/stream (Ctrl+C - стоп)..."

HelpText = """Команды HoneyForge CLI:

  help                         - эта справка
  clear                        - очистить экран
  exit | quit                  - выход
  health                       - GET /health
  me                           - текущий оператор (Bearer)
  logout                       - сбросить Bearer-токен

Профили (конструктор):
  profile-schema               - схема блоков конструктора
  profile-list                 - список профилей
  profile-show <id>            - показать профиль
  profile-create --file f.json
  profile-create --name N --level low|medium|high --port P [--service ssh]
  profile-delete <id>          - удалить профиль

Pairing / ловушки:
  pair-confirm <device_code> [--name trap] [--profile-id UUID]
  traps-list                   - список ловушек и статусы
  trap-show <trap_id>
  trap-bind <trap_id> <profile_id>

События:
  events-list [--trap-id] [--type] [--source-ip] [--limit N]
  events-tail                  - realtime SSE-лента

Перед командами нужен login (пароль при старте CLI).
API_BASE задаётся в .env (по умолчанию http://127.0.0.1:8000).
"""
