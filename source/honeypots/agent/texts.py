
MSG_TOKEN_SAVED = "Токен сохранён в {path}"
MSG_TOKEN_LOADED = "Токен загружен из {path} (trap_id={trap_id})"
MSG_ERR_NO_AGENT_TOKEN = "в state-файле {path} нет agent_token"

MSG_PAIR_STARTED = "Pairing стартовал. Подтверди код у оператора: {code}"
MSG_PAIR_WAIT = "Жду confirm... ({attempt})"
MSG_PAIR_DONE = "Pairing готов. trap_id={trap_id}"
MSG_PAIR_TIMEOUT = "таймаут ожидания confirm ({wait_sec}s). Код был: {code}"

MSG_HEARTBEAT_OK = "Heartbeat ok, config_version={version}"
MSG_EVENTS_ACCEPTED = "События приняты: accepted={accepted}"
MSG_EVENTS_QUEUED = "Событие в буфере (центр недоступен): {event_type}"

MSG_ERR_NO_TOKEN = "нет agent_token - сначала пройди pairing"
MSG_ERR_HTTP = "HTTP {status}: {body}"

MSG_DEBUG_REQUEST = "запрос: {method} {url}"
MSG_ERR_NO_TOKEN_CLIENT = "нет agent_token - сначала пройди pairing"

MSG_BUFFER_ADDED = "в буфер добавлено событие: {event_type}"
MSG_BUFFER_SENT = "из буфера отправлено: {count}"
MSG_BUFFER_PENDING = "в буфере неотправленных: {count}"

MSG_LOW_STARTED = "Low-ловушка слушает порт {port} (баннер: {banner})"
MSG_LOW_STOPPED = "Low-ловушка остановлена (порт {port})"
MSG_LOW_CONNECT = "подключение: {source_ip}:{source_port} -> порт {port}"
MSG_LOW_BANNER_SENT = "баннер отправлен: {banner}"

MSG_ERR_NO_ASYNCSSH = "для входа по ssh нужен пакет asyncssh: python3 -m pip install --user --break-system-packages -r requirements.txt"
MSG_FAKE_SSH_STARTED = "фейковый ssh слушает порт {port}, hostname={host}"
MSG_FAKE_SSH_AUTH = "вход принят: user={user} ip={ip}"

MSG_SHELL_WELCOME = "Welcome to {host}\nLast login from {ip}\n"
MSG_SHELL_PROMPT = "{user}@{host}:{cwd}{suffix} "
MSG_SHELL_LOGOUT = "logout\n"
MSG_SHELL_HELP = "commands: ls pwd cd cat whoami id hostname uname echo exit\n"
MSG_SHELL_NOT_FOUND = "bash: {cmd}: command not found\n"
MSG_SHELL_NO_FILE = "cat: {path}: No such file or directory\n"
MSG_SHELL_NOT_DIR = "bash: cd: {path}: Not a directory\n"
MSG_SHELL_CAT_USAGE = "cat: missing file operand\n"
MSG_SHELL_ID = "uid=1000({user}) gid=1000({user}) groups=1000({user})\n"
MSG_SHELL_UNAME = "Linux {host} 5.15.0-91-generic #101 SMP x86_64 GNU/Linux\n"
MSG_SHELL_ISSUE = "Ubuntu 22.04.3 LTS \\n \\l\n"
MSG_SHELL_README = "quarterly notes. do not delete.\n"

MSG_AGENT_STARTED = "Агент запущен. Версия: {version}"
MSG_AGENT_TOKEN_OK = "Токен загружен, trap_id={trap_id}"
MSG_AGENT_NO_SERVICES = "в профиле нет активных сервисов - нечего слушать"
MSG_AGENT_SERVICE_START = "запускаю сервис: {name} на порту {port}"
MSG_AGENT_CONFIG_OK = "конфиг получен: profile={name} level={level}"
MSG_AGENT_STOPPED = "агент остановлен"
