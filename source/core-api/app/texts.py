MSG_HEALTH_OK = "ok"
MSG_DEBUG_BOOT = "core-api starting"
MSG_DB_OK = "database reachable"
MSG_DB_FAIL = "database unreachable"

MSG_AUTH_BAD_PASSWORD = "неверный пароль"
MSG_AUTH_REQUIRED = "нужна авторизация оператора"
MSG_AUTH_BAD_TOKEN = "недействительный токен"

MSG_PROFILE_NOT_FOUND = "профиль не найден"
MSG_PROFILE_HIGH_UNAVAILABLE = "уровень high недоступен: блок emulation ещё не подключён"
MSG_PROFILE_LEVEL_MISMATCH = (
	"interaction_level={declared} не совпадает с модулями (фактически {actual}). "
	"low - только баннер, medium - вход, shell, http или база"
)
MSG_PROFILE_DUP_PORT = "порты включённых сервисов должны быть уникальными"
MSG_PROFILE_DUP_SERVICE_ID = "id сервисов должны быть уникальными"
MSG_PROFILE_DUP_CRED = "id учётных данных должны быть уникальными"
MSG_PROFILE_UNKNOWN_CREDS = "сервис {service_id} ссылается на неизвестные credentials: {missing}"
MSG_PROFILE_SSH_BANNER = "у SSH модуль banner обязателен: это часть handshake"
MSG_PROFILE_SSH_SHELL_AUTH = "SSH shell требует включённый auth"
MSG_PROFILE_AUTH_LIST = "режим allow_listed требует непустой credential_ids"
MSG_PROFILE_DELAY = "delay_ms_max должен быть не меньше delay_ms_min"
MSG_TRAP_NOT_FOUND = "ловушка не найдена"
MSG_PAIRING_NOT_FOUND = "сессия pairing не найдена"
MSG_PAIRING_EXPIRED = "код pairing истёк"
MSG_PAIRING_BAD_CODE = "неверный device_code"
MSG_PAIRING_NOT_READY = "pairing ещё не подтверждён оператором"
MSG_AGENT_UNAUTHORIZED = "агент не авторизован"
MSG_AGENT_NO_PROFILE = "к ловушке не привязан профиль"

MSG_DEPLOY_NEED_HOST = "нужен IP хоста"
MSG_DEPLOY_NEED_PASSWORD = "нужен пароль SSH"
MSG_DEPLOY_BAD_CENTER = (
	"адрес центра должен быть http:// или https:// без кавычек и пробелов"
)
MSG_DEPLOY_AUTH = "SSH не пустил: проверь логин, пароль и порт"
MSG_DEPLOY_CONNECT = "нет соединения с {host}:{port}: {detail}"
MSG_DEPLOY_RUN = "хост ответил, но агент не встал: {detail}"
MSG_DEPLOY_CODE_TIMEOUT = (
	"агент запущен, код pairing в логе не появился; смотри pair-list"
)

MSG_FS_PACK_NOT_FOUND = "пакет файловой системы не найден"
MSG_FS_PACK_TOO_LARGE = "архив больше {limit_mib} MiB"
MSG_FS_PACK_BAD_FORMAT = "нужен архив .zip или .tar.gz / .tgz"
MSG_FS_PACK_EMPTY = "пустой файл архива"
MSG_FS_PACK_UNKNOWN = "shell.fs_pack ссылается на неизвестный пакет: {token}"
MSG_FS_PACK_BAD_NAME = "нужно имя пакета"
