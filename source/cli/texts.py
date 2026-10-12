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
ProfileUpdatedText = "Профиль обновлён: {profile_id}"
ProfileDeletedText = "Профиль удалён: {profile_id}"
ProfileCreateUsageText = (
    "нужны --file ИЛИ --name --port "
    "[--service ssh|http|tcp_banner|postgres|redis|mysql] [--level low|medium] "
    "[--services postgres,redis,mysql] "
    "[--auth off|allow_all|allow_listed|second_attempt_sticky] "
    "[--username U --password P] [--banner TEXT]"
)
ProfileUpdateUsageText = "нужны --file и/или --name, --description"
ProfileHighUnavailableText = "уровень high недоступен: блок emulation ещё не подключён"
ProfileHttpNeedsMediumText = "http, postgres, redis и mysql всегда medium"
ProfileBannerNeedsLowText = "tcp_banner это только уровень low, без входа"
ProfileServiceUnknownText = "сервис должен быть ssh, http, tcp_banner, postgres, redis или mysql"
ProfilePortConflictText = "порт {port} уже занят ловушкой {first}, {second} туда вставать не может"
ProfileServicesNeedNameText = "для --services нужно --name"
ProfileOnePortText = "--port задаёт порт одной ловушки. Для нескольких порты стандартные: postgres 5432, redis 6379, mysql 3306"
ProfileListedNeedsCredsText = "allow_listed требует --username и --password"
ProfilePasswordRequiredText = "вместе с --username нужен --password"
ProfileAuthNeedsMediumText = "вход и shell дают уровень medium, для low уберите --auth"
ProfileDelayPairText = "укажите оба значения: --delay-min и --delay-max"
ProfileDelayOrderText = "--delay-max должен быть не меньше --delay-min"
ProfileAuthOnBannerText = "у tcp_banner нет модуля входа"
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
    "Роль задаёт стартовый набор. На следующем шаге можно оставить одну ловушку "
    "или включить несколько. Уровень low или medium получится из модулей."
)

SetupStep2Header = "Этап 2/5 - Модули сервиса"

SetupStep2TipService = (
    "Сервис собирается по слотам. SSH: banner, потом auth, потом shell. "
    "HTTP: personality, auth, routes. Базы: banner, auth, session. "
    "Несколько ловушек живут на одном узле, если у каждой свой порт."
)
SetupTrapListHelp = """
Ловушки на этом узле. Несколько номеров через запятую:
  1) ssh          22
  2) http         8080
  3) tcp_banner   2121
  4) postgres     5432
  5) redis        6379
  6) mysql        3306
"""
SetupAskTrapSetText = "Какие ловушки включить"
SetupTrapSetEmptyText = "Нужна хотя бы одна ловушка"
SetupTrapSetBadText = "Не понял список. Пример: 1,4,5"
SetupTrapProgressText = "Ловушка {index}/{total}"

SetupStep2TipCreds = (
    "Слабые учётки-приманки специально оставляют на Mid: "
    "root/admin, ubuntu/ubuntu. Реальные прод-секреты сюда не класть."
)

SetupAuthModesHelp = """
Модуль auth:
  0) off - слот выключен
  1) allow_all - пускать любой пароль
  2) allow_listed - только учётка-приманка
  3) second_attempt_sticky - со второй попытки, дальше только этот пароль с этого IP
"""
SetupAuthBecomesLowText = "Вход выключен. SSH останется баннером, профиль будет low."
SetupShellNeedsAuthText = "Shell без auth не бывает. Слот shell выключен."
SetupRoutesTipText = "Модуль routes отдаёт / и страницу входа. Отдельный список путей тут не собирается."

SetupStep3Header = "Этап 3/5 - Сокрытие трафика канала"

SetupConcealHelp = """
Способы блока mask, каждый можно выключить:
  jitter         - разброс паузы между beacon
  cover          - лишние GET (favicon, robots) между beacon
  path_rotation  - heartbeat по путям /v1/metrics и /cdn/edge-check
  mimicry        - обычный User-Agent браузера
  process_mask   - имя процесса на хосте ловушки
"""

SetupAskJitterText = "Включить jitter"
SetupAskBeaconText = "Как часто узел связывается с центром, сек"
SetupAskJitterPctText = "Разброс по времени, %"
SetupAskCoverText = "Включить cover-трафик"
SetupAskCoverUrlsText = "Cover URL через запятую"
SetupAskPathRotationText = "Ротировать путь heartbeat"
SetupAskMimicryText = "Маскировать User-Agent под браузер"
SetupAskUserAgentText = "User-Agent"
SetupAskProcessMaskText = "Скрыть имя процесса"
SetupAskProcessNameText = "Имя процесса"
SetupAskProcessNameAgainText = "Имя процесса ещё раз"
SetupProcessNameBadText = "Имя выдаёт приманку. Лучше: svchost, systemd-net, mDNSResponder."
SetupCoverUrlsDefault = "/favicon.ico, /robots.txt"
SetupUserAgentDefault = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DispMaskMethodsTitle = "способы сокрытия"

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

SetupSshInstallTip = (
	"CLI зайдёт на хост ловушки по SSH и сам скачает агент из центра. "
	"Нужны IP, логин, пароль и порт SSH. Это машина, которой ты управляешь."
)
SetupAskSshInstallText = "Поставить агент по SSH"
SetupAskSshHostText = "IP хоста ловушки"
SetupAskSshUserText = "Логин SSH"
SetupAskSshPasswordText = "Пароль SSH: "
SetupAskSshPortText = "Порт SSH"
SetupAskReachableCenterText = "Адрес центра, который видит хост ловушки"
SetupSshLocalCenterText = (
	"С хоста ловушки 127.0.0.1 - это он сам, не твой центр. "
	"Укажи адрес, по которому до него достучаться, например http://10.0.0.1:8000."
)
SetupSshHostKeyText = "Ключ {host}: {fingerprint}. Принимаю для этой установки."
SetupSshConnectingText = "Подключаюсь к {user}@{host}:{port} и ставлю агент..."
SetupSshCodeText = "Код с хоста: {code}"
SetupSshFailedText = "Поставить по SSH не вышло: {detail}"
SetupSshManualFallbackText = "Можно поставить вручную командой с карточки."
DeployNeedHostText = "Нужен IP хоста."
DeployNeedPasswordText = "Нужен пароль SSH."
DeployBadCenterText = "Адрес центра должен быть http:// или https:// без кавычек и пробелов."
DeployNoSshText = "Нет команды ssh. Нужен OpenSSH на машине оператора."
DeploySshAuthText = "SSH не пустил: проверь логин, пароль и порт."
DeploySshConnectText = "Нет соединения с {host}:{port}: {detail}"
DeploySshRunText = "Хост ответил, но агент не встал: {detail}"
DeployCodeTimeoutText = "Агент запущен, код pairing в логе не появился. Смотри pair-list."

SetupInstallCard = """
+-----------------------------------------------------------+
|  INSTALL CARD                                             |
|  Узел:     {trap_name}
|  Роль:     {role_label}
|  Профиль:  {profile_name}
|  Центр:    {api_base}
|                                                           |
|  НА ХОСТЕ ЛОВУШКИ:                                        |
|                                                           |
|    curl -fsSL {api_base}/downloads/install.sh | \\        |
|      API_BASE={api_base} sh                               |
|                                                           |
|  Скрипт скачает агент из /downloads/, запишет .env        |
|  и запустит pairing. Код подтверди здесь.                 |
+-----------------------------------------------------------+
"""

SetupRolePresetsHelp = """
Доступные роли приманки:
  1) corp-ssh    - SSH: banner + sticky-вход + shell
  2) edge-http   - HTTP: personality + вход по приманке + routes
  3) scan-bait   - SSH: только модуль banner (low)
  4) custom      - самому включить слоты ssh / http / tcp_banner / базы
  5) data-stores - сразу Postgres, Redis и MySQL на разных портах
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
  deploy --host IP --user root [--port 22] [--api-base URL]
                               - поставить агент по SSH (пароль спросит)
  exit | quit                  - выход
  health                       - GET /health
  me                           - текущий оператор (Bearer)
  logout                       - сбросить Bearer-токен

Профили (конструктор, слоты сервиса):
  profile-schema               - типы сервисов, режимы auth, пример
  profile-list                 - список профилей
  profile-show <id>            - показать профиль и модули
  profile-create --file f.json
  profile-create --name N --port P --service ssh|http|tcp_banner|postgres|redis|mysql
  profile-create --name N --services postgres,redis,mysql
      [--level low|medium]
      [--auth off|allow_all|allow_listed|second_attempt_sticky]
      [--username U --password P] [--banner TEXT]
      [--server S] [--auth-path /admin]
      [--delay-min MS --delay-max MS] [--sticky-ttl HOURS] [--no-shell]
  profile-update <id> [--file f.json] [--name N] [--description TEXT]
  profile-delete <id>          - удалить профиль
  Уровень считается из модулей: баннер = low, вход/shell/http = medium.
  high (emulation) пока не принимается.

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
