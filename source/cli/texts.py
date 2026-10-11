import os

from colorama import Fore, Style
from random import *


def print_Logo():
    selection = randint(1, 3)
    if selection == 1:
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
    elif selection == 2:
        print(Fore.MAGENTA + r"""
      ███  ███ ██████▄  ██████▄   ▄██████ ███  ███       ▄██████ ██████▄  ██████▄   ▄██████  ▄██████
      ▒▒▒  ▒▒▒ ▄▄▄  ▒▒▒ ▄▄▄  ▒▒▒ ▒▒▒  ▀▀▀ ▒▒▒▄ ▒▒▒      ▒▒▒  ▀▀▀ ▄▄▄  ▒▒▒ ▄▄▄  ▒▒▀ ▒▒▒  ▀▀▀ ▒▒▒  ▀▀▀
      ████████ ███  ███ ███  ███ █████▀    ▀██████      █████▀   ███  ███ ██████▄  ███ ████ █████▀
      ▒▒▒  ▒▒▒ ▒▒▒  ▒▒▒ ▒▒▒  ▒▒▒ ▒▒▒  ▄▄▄     ▄▒▒▒      ▒▒▒      ▒▒▒  ▒▒▒ ▒▒▒  ▒▒▒ ▒▒▒  ▒▒▒ ▒▒▒  ▄▄▄
      ███  ███  ▀████▀  ███  ███  ▀██████ ██████▀       ███       ▀████▀  ███  ███  ▀██████  ▀██████"""
        + Style.RESET_ALL)
    elif selection == 3:
        print(Fore.MAGENTA + r"""
                                            ;.         .'
                too BEE-zy to ......    ;-_ ; \       /  _
                              ;.         .` `-. \    .:.-'
                ;.        ;.' ; \       /  `.-.`.\, /  "\
            ;-_ ; \       /` _-. \    .:.-'  '-._\/;\   /
            ` `-. \    .:.-'.-.`.\, /  "\     ,;\\\|`-' ;.         .'
              `.-.`.\, /  "\  '-._\/;\   /    (\\\.'/;-_ ; \       /  _
                '-._\/;\   /    ,;\\\|`-'   ;. `._.'  `.`-. \    .:.-'
                  ,;\\\|`-' ;. (\\\.'/ .'-_ ; \       /`.-.`.\, /  "\
                (\\\.'/;-_ ; \ `._.' /  _ `-. \    .:.-''-._\/;\   /
              ;.  `._.'  .'`-. \    .:.-' `.-.`.\, /  "\   ,;\\\|`-'
          ;-_ ; \       / `_-.`.\, /  "\    '-._\/;\   /  (\\\.'/
          ` `-. \    .:.-' '-._\/;\   /      ,;\\\|`-' ;. `._.'   .'
            `.-.`.\, /  "\    ,;\\\|`-'  ;.  (\\\.'/;-_ ; \       /  _
              '-._\/;\   /   (\\\.'/ ;-_ ; \  `._.'/ `_`-. \    .:.-'
                ,;\\\|`-'  ;. `._.'   .'`-. \    .:.-'`.-.`.\, /  "\
              (\\\.'/ ;-_ ; \       / `_-.`.\, /  "\   '-._\/;\   /
              mx`._.'   ` `-. \    .:.-' '-._\/;\   /     ,;\\\|`-'
                        `.-.`.\, /  "\    ,;\\\|`-'     (\\\.'/
                          '-._\/;\   /   (\\\.'/         `._.'
                            ,;\\\|`-'     `._.'
                            (\\\.'/
                            `._.'            ... BUZZ ?""" + Style.RESET_ALL)


def clear_Screen():
    os.system("cls" if os.name == "nt" else "clear")

CoreApiErrorText = "Не удалось подключиться к CoreAPI.\n" \
"Проверьте, что CoreAPI запущен.\n" \
"Попробуйте >cd core-api\n"\
">uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

PasswordErrorText = "Неверный пароль. Попробуйте ещё раз."

LoginSuccessText = "Вход выполнен. Добро пожаловать в HoneyForge."

WelcomeText = "Введите help - список команд. Новичкам: setup (развёртывание ловушки)."

LogoutSuccessText = "Токен сброшен (logout)."

MeErrorText = "me: {detail}"

MsgApiError = "API: {detail}"

ProfileCreatedText = "Профиль создан: {profile_id}"

ProfileDeletedText = "Профиль удалён: {profile_id}"

PairConfirmText = "Pairing подтверждён."

PairListHeaderText = "Входящие pairing ({total}), status={status}:"

PairListEmptyText = "Нет pairing со status={status}."

TrapBoundText = "Профиль привязан к ловушке."

EventsTailHintText = "Слушаю SSE /api/v1/events/stream (Ctrl+C - стоп)..."

EventsTailStoppedText = "events-tail остановлен."

DispEmptyListText = "Пусто: {what}."

DispProfilesHeaderText = "Профили ({total})"

DispTrapsHeaderText = "Ловушки ({total})"

DispEventsHeaderText = "События ({shown} из {total})"

DispSchemaHeaderText = "Схема конструктора профилей"

DispPairConfirmHintText = "Дальше: traps-list / trap-show - статус узла в парке."

SetupIntroText = """
РАЗВЁРТЫВАНИЕ ЛОВУШКИ
=====================
Сценарий оператора SOC:
  1) спроектировать приманку
  2) выдать установку на хост в сегменте-ловушке
  3) принять узел в парк
  4) убедиться, что ловушка в строю и пишет активность

Пустой Enter - значение по умолчанию. q - отмена.
"""

SetupAbortText = "Развёртывание прервано. Узел можно донастроить позже через setup."

SetupDoneText = "Ловушка в парке: {trap_name}"

SetupStep1Header = "Этап 1/5 - Объект и роль приманки"

SetupStep1TipSite = (
    "Ловушка живёт в изолированном сегменте (DMZ/lab), не в прод-сети. "
    "Имя узла должно выглядеть как обычный хост: dmz-ssh-04, web-edge-2."
)

SetupStep1TipRole = (
    "Роль задаёт, чем приманка притворяется для атакующего. "
    "От этого зависит глубина сессии и какие артефакты вы соберёте."
)

SetupStep2Header = "Этап 2/5 - Лицо сервиса (что видит атакующий)"

SetupStep2TipService = (
    "Баннер и порт - первое, что снимает сканер. "
    "Бери правдоподобную версию ОС/сервиса, не 'HoneyForge-SSH'."
)

SetupStep2TipCreds = (
    "Слабые учётки-приманки специально оставляют на Mid: "
    "root/admin, ubuntu/ubuntu. Реальные прод-секреты сюда не класть."
)

SetupStep3Header = "Этап 3/5 - Скрытность канала управления"

SetupStep3TipMask = (
    "Атакующий на хосте не должен узнать, что узел 'звонит' в центр. "
    "Канал маскируется под обычный HTTPS/CDN, процесс агента - под системный."
)

SetupStep3TipJitter = (
    "Ровный beacon раз в N секунд - красный флаг для аналитика. "
    "Оставь разброс (jitter), чтобы трафик не был метрономом."
)

SetupStep4Header = "Этап 4/5 - Установка на хост и приём в парк"

SetupStep4TipInstall = (
    "Дальше работа на машине-приманке: ставишь агент, он запрашивает код регистрации. "
    "Код приносишь сюда - как approve нового устройства."
)

SetupStep4TipCodeTtl = (
    "Код регистрации короткоживущий. Не подтверждён вовремя - запроси новый с хоста."
)

SetupStep4WaitingText = "Ожидаю запрос регистрации от хоста..."

SetupStep4ApprovedText = "Узел принят в парк: {trap_name} ({trap_id})"

SetupStep5Header = "Этап 5/5 - Ввод в строй и контрольная проверка"

SetupStep5TipOnline = (
    "online = хост на связи и тянет конфиг. "
    "pending = код приняли, но агент ещё не отметился. offline = пропал beacon."
)

SetupStep5TipProbe = (
    "Контроль: с соседней машины в lab стукнись в приманку "
    "(ssh/curl на её порт) или дождись сканера - в ленте должно появиться событие."
)

SetupInstallCard = """
+-----------------------------------------------------------+
|  INSTALL CARD                                             |
|  Узел:     {trap_name}
|  Роль:     {role_label}
|  Профиль:  {profile_name}
|  Центр:    {api_base}
|                                                           |
|  НА ХОСТЕ ЛОВУШКИ (не на этой рабочей станции):           |
|                                                           |
|    cd source/honeypots                                    |
|    set API_BASE={api_base}
|    python fake_agent.py                                   |
|                                                           |
|  Без токена рядом - pairing (код на экран); с токеном -   |
|  heartbeat + события. Код подтверди в операторском CLI.   |
|                                                           |
|  * пока вместо боевого пакета агента - стенд fake_agent   |
+-----------------------------------------------------------+
"""

SetupRolePresetsHelp = """
Доступные роли приманки:
  1) corp-ssh     - корпоративный SSH (medium) - креды, попытки входа
  2) edge-http    - веб-админка / edge HTTP (medium)
  3) scan-bait    - только порты и баннеры (low) - детектор сканов
  4) custom       - ручная настройка
"""


def print_SetupTip(text: str) -> None:
    print(Fore.YELLOW + "  *  " + Style.RESET_ALL + text)


def print_Attention(text: str) -> None:
    print(Fore.RED + Style.BRIGHT + "  !  " + Style.RESET_ALL + Fore.YELLOW + text + Style.RESET_ALL)


def print_OpsLine(label: str, value: str) -> None:
    print(f"  {Fore.CYAN}{label:<12}{Style.RESET_ALL} {value}")


HelpText = """Команды HoneyForge CLI:

  help                         - эта справка
  clear                        - очистить экран
  logo                         - показать логотип
  setup | guide                - развернуть ловушку (мастер установки)
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
  pair-list [--status pending|confirmed|completed|expired|all]
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
