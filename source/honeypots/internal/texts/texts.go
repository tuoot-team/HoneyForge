package texts

const (
	MsgTokenSaved      = "Токен сохранён в %s"
	MsgTokenLoaded     = "Токен загружен из %s (trap_id=%s)"
	MsgErrNoAgentToken = "в state-файле %s нет agent_token"

	MsgPairStarted = "Pairing стартовал. Подтверди код у оператора: %s"
	MsgPairWait    = "Жду confirm... (%d)"
	MsgPairDone    = "Pairing готов. trap_id=%s"
	MsgPairTimeout = "таймаут ожидания confirm (%ds). Код был: %s"

	MsgHeartbeatOk    = "Heartbeat ok, config_version=%v"
	MsgEventsAccepted = "События приняты: accepted=%v"
	MsgEventsQueued   = "Событие в буфере (центр недоступен): %s"

	MsgErrNoToken       = "нет agent_token - сначала пройди pairing"
	MsgErrHTTP          = "HTTP %d: %s"
	MsgErrNoTokenClient = "нет agent_token - сначала пройди pairing"

	MsgDebugRequest = "запрос: %s %s"

	MsgBufferAdded   = "в буфер добавлено событие: %s"
	MsgBufferSent    = "из буфера отправлено: %d"
	MsgBufferPending = "в буфере неотправленных: %d"

	MsgLowStarted    = "Low-ловушка слушает порт %d (баннер: %s)"
	MsgLowStopped    = "Low-ловушка остановлена (порт %d)"
	MsgLowConnect    = "подключение: %v:%v -> порт %d"
	MsgLowBannerSent = "баннер отправлен: %s"

	MsgFakeSshStarted = "фейковый ssh слушает порт %d, hostname=%s"
	MsgFakeSshAuth    = "вход принят: user=%s ip=%v"

	MsgShellWelcome  = "Welcome to %s\nLast login from %s\n"
	MsgShellPrompt   = "%s@%s:%s%s "
	MsgShellLogout   = "logout\n"
	MsgShellHelp     = "commands: ls pwd cd cat whoami id hostname uname echo exit\n"
	MsgShellNotFound = "bash: %s: command not found\n"
	MsgShellNoFile   = "cat: %s: No such file or directory\n"
	MsgShellNotDir   = "bash: cd: %s: Not a directory\n"
	MsgShellCatUsage = "cat: missing file operand\n"
	MsgShellID       = "uid=1000(%s) gid=1000(%s) groups=1000(%s)\n"
	MsgShellUname    = "Linux %s 5.15.0-91-generic #101 SMP x86_64 GNU/Linux\n"
	MsgShellIssue    = "Ubuntu 22.04.3 LTS \\n \\l\n"
	MsgShellReadme   = "quarterly notes. do not delete.\n"

	MsgAgentStarted      = "Агент запущен. Версия: %s"
	MsgAgentNoServices   = "в профиле нет активных сервисов - нечего слушать"
	MsgAgentServiceStart = "запускаю сервис: %s на порту %d"
	MsgAgentConfigOk     = "конфиг получен: profile=%s level=%s"
	MsgAgentStopped      = "агент остановлен"
	MsgAgentReload       = "получена команда reload_config - перечитываю профиль"
	MsgPairAutoStart     = "токен не найден - запускаю pairing"
	MsgUsage             = "использование: %s [pair|run]  (без аргументов = run; без токена сам сделает pair)"
	MsgApiBase           = "API: %s"
)
