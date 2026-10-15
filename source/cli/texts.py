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

PasswordErrorText = "Неверный логин или пароль. Попробуйте ещё раз."

LoginUsernamePrompt = "Логин: "
LoginPasswordPrompt = "Пароль: "

LoginSuccessText = "Вход выполнен. Добро пожаловать в HoneyForge."

UserListHeaderText = "Пользователи:"
UserListEmptyText = "Пользователей нет"
UserCreatedText = "Создан пользователь {username} ({user_id}), роль {role}"
UserUpdatedText = "Пользователь {username}: роль {role}"
UserDisabledText = "Пользователь {username}: {state}"

RoleListHeaderText = "Роли:"
RoleListEmptyText = "Ролей нет"
RolePermsHeaderText = "Каталог прав:"
RoleCreatedText = "Создана роль {name} ({role_id})"
RoleUpdatedText = "Роль {name} обновлена"
RoleDeletedText = "Роль {role_id} удалена"

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
    "[--username U --password P] [--banner TEXT]; "
    "или --name --level high --image-token vmi_..."
)
ProfileUpdateUsageText = "нужны --file и/или --name, --description"
ProfileHighNeedsImageText = "для --level high нужен --image-token (см. vm-image-list)"
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
TrapOwnerSetText = "Владелец ловушки обновлён."

EventsTailHintText = "Слушаю SSE /api/v1/events/stream (Ctrl+C - стоп)..."

EventsTailStoppedText = "events-tail остановлен."

EventsExportSavedText = "Экспорт сохранён: {path} ({bytes} байт)"

PersonalityPackListEmptyText = "Нет personality packs."
PersonalityPackListHeaderText = "Personality packs:"
SetupAskPersonalityPackText = "Пресет личности (Enter - без пресета)"
SetupPersonalityPackTipText = "Пресет дозаполнит пустые banner/HTTP personality/mask. Список: personality-pack-list"

WipeConfirmLogsText = "Удалить события и журнал аудита? (y/N)"
WipeConfirmResetText = (
	"Удалить профили, ловушки, pairing, команды, события и журнал? (y/N)"
)
WipeAbortedText = "Отменено."
LogsClearedText = "Логи очищены: события {events}, журнал {audit_log}."
DbResetText = (
	"База сброшена: профили {profiles}, ловушки {traps}, "
	"pairing {pairing_sessions}, команды {trap_commands}, "
	"события {events}, журнал {audit_log}."
)

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
SetupDoneTipText = "Смена: traps-list / trap-show / trap-set-owner / events-tail / pair-list"

SetupStep1Header = "Этап 1/5 - Объект"

SetupStep1TipSite = (
	"Ловушка живёт в изолированном сегменте (DMZ/lab), не в прод-сети. "
	"Имя узла должно выглядеть как обычный хост: dmz-ssh-04, web-edge-2."
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

SetupAskLinkCredsText = "Связать одну учётку-приманку между выбранными сервисами"
SetupLinkCredsTipText = (
	"Один логин/пароль на SSH/HTTP/БД мини-парка - пентестер переходит с сервиса на сервис теми же кредами."
)
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
SetupFsPackHelp = """
Пакет файловой системы для shell:
  1) без файловой системы - встроенное дерево ubuntu-22.04
  2) создать новую - загрузить zip/tar.gz с этой машины
  3) использовать существующую - пакет уже на центре
"""
SetupAskFsPackModeText = "Вариант пакета FS"
SetupAskFsPackFileText = "Путь к архиву (.zip / .tar.gz)"
SetupAskFsPackNameText = "Имя пакета"
SetupAskFsPackPickText = "Номер или token пакета"
SetupFsPackUploadOkText = "Загружен пакет {token} ({name})"
SetupFsPackNoExistingText = "На центре нет пакетов. Создайте новый или выберите встроенный."
SetupFsPackBadPickText = "Не понял выбор. Введите номер из списка или token fsp_..."
SetupFsPackBadFileText = "Нужен существующий файл .zip или .tar.gz / .tgz"
SetupRoutesTipText = "Модуль routes отдаёт / и страницу входа. Отдельный список путей тут не собирается."
SetupHttpPlainText = "Это обычный HTTP, не HTTPS. Проверка: curl http://IP-узла:{port}/"

FsPackListHeaderText = "Пакеты файловой системы:"
FsPackListEmptyText = "Пакетов пока нет"
FsPackUploadedText = "Загружен {token} ({name}, {size})"
FsPackDeletedText = "Удалён пакет {token}"

VmImageListHeaderText = "Образы VM (OVA):"
VmImageListEmptyText = "Образов пока нет - vm-image-upload --file disk.ova"
VmImageUploadedText = "Загружен {token} ({name}, {size})"
VmImageDeletedText = "Удалён образ {token}"
TrapVmCommandText = "Команда vm_{action} поставлена в очередь ловушки {trap_id}"
DeployHighVmNoteText = (
	"High VM: на хосте ловушки нужны VirtualBox и VBoxManage в PATH "
	"(агент импортирует OVA и управляет VM)."
)
SetupAskHighVmText = "High VirtualBox VM вместо medium-сервисов"
SetupAskImageTokenText = "Токен образа (vmi_... из vm-image-list)"
SetupAskVmNameText = "Имя VM в VirtualBox"
SetupAskVmSnapshotText = "Имя snapshot (чистый)"
SetupAskRdpHostPortText = "Порт RDP на хосте ловушки"
SetupAskVmAutoStartText = "Стартовать VM после bind профиля"
SetupHighNeedsImageText = "Сначала загрузите образ: vm-image-upload --file disk.ova"
SetupHighConfiguredText = "High emulation: {vm_name} ← {image_token}"

SetupStep3Header = "Этап 3/5 - Сокрытие трафика канала"

SetupConcealHelp = """
Способ доставки логов:
  1) agent   - ловушка сама шлёт batch (можно включить jitter/cover/...)
  2) courier - третий сервер забирает буфер по SSH; классический mask выключается

В режиме agent доступны способы mask:
  jitter         - разброс паузы между beacon
  cover          - лишние GET (favicon, robots) между beacon
  path_rotation  - heartbeat по путям /v1/metrics и /cdn/edge-check
  mimicry        - обычный User-Agent браузера
  process_mask   - имя процесса на хосте ловушки
"""

SetupAskDeliveryText = "Доставка логов (1=agent, 2=courier)"
SetupAskCollectIntervalText = "Как часто курьер забирает логи, сек"
SetupAskCreateCourierText = "Создать нового курьера сейчас"
SetupAskCourierNameText = "Имя курьера"
SetupAskCourierDeployText = "Поставить курьера на третий хост по SSH"
SetupAskCourierHostText = "IP третьего хоста (курьер, не ловушка)"
SetupAskCourierCenterText = "Адрес центра, который видит хост курьера"
SetupAskTrapCourierSshText = "Задать SSH ловушки для визитов курьера"
SetupCourierCreatedText = "Курьер принят в парк: {name} ({courier_id})"
SetupCourierDeployTip = (
	"Курьер ставится на ОТДЕЛЬНУЮ машину (не на ловушку): центр зайдёт по SSH, "
	"скачает бинарь и подхватит код pairing. "
	"Адрес центра - публичный канал (обычно https://host без :8088)."
)
SetupCourierConnectingText = (
	"Центр подключается к {user}@{host}:{port} и ставит курьера..."
)
SetupCourierDeployFailedText = (
	"Поставить курьера по SSH не вышло: {detail}. "
	"Можно позже: courier-deploy / courier-confirm <код>."
)
SetupCourierManualLaterText = "Курьера можно принять позже: courier-confirm <код> с хоста."
SetupDeliveryCourierTip = (
	"В режиме courier ловушка не шлёт события сама. "
	"Курьер по расписанию заходит по SSH, забирает буфер и чистит следы визита."
)

CourierListEmptyText = "Курьеров пока нет."
CourierListHeaderText = "Курьеры ({total}):"
CourierPairListHeaderText = "courier pairing ({total}), status={status}:"
CourierPairListEmptyText = "Нет courier pairing со status={status}."
CourierConfirmText = "Курьер подтверждён."
CourierDeployText = "Курьер поставлен. Код: {code}"
CourierDeployNextText = "courier-confirm {code}"
DeployPairNextText = "pair-confirm {code}"
DeployNoDeviceCodeText = "в ответе deploy нет device_code"
CourierShowHintText = "Дальше: courier-list / pair-list курьера через courier-confirm."
TrapCourierSshSavedText = "SSH ловушки для курьера сохранён."
SetupCourierCodeMissingText = "код в логе не найден"
SetupAskPairListRetryText = "Выбрать код из pair-list сейчас"
SetupCourierCommissionOkText = "Профиль на месте; логи заберёт курьер."
SetupApproveNodeText = "Принимаю узел '{trap_name}' и накатываю конфиг приманки..."
SetupHostWillFinishText = "На хосте агент завершит регистрацию и подтянет конфиг сам."

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
SetupProcessNameBadText = "Имя выдаёт приманку. Лучше: metricsd, systemd-net, mDNSResponder."
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
SetupStep4BadCodeText = (
	"Код {code} не принят центром (устарел или был из старого agent.log)."
)
SetupStep4BadCodeTipText = (
	"На ловушке: grep 'Подтверди код' /var/lib/metricsd/daemon.log | tail -1 "
	"затем pair-confirm <код> --name <позывной> --profile-id <UUID профиля>"
)

SetupStep4TipOwner = (
	"Владелец ловушки - оператор, который принял узел. "
	"Без права traps.all другие увидят только свои ловушки. "
	"Переназначить: trap-set-owner или шаг ниже."
)

SetupAskOwnerReassignText = "Назначить другого владельца"
SetupAskOwnerUserIdText = "UUID пользователя-владельца"
SetupOwnerUsersEmptyText = "Нет пользователей для назначения."
SetupOwnerUsersListDeniedText = (
	"Список пользователей недоступен (нужно users.write). "
	"Введи UUID вручную или назначь позже: trap-set-owner."
)
SetupOwnerSetOkText = "Владелец обновлён."
SetupOwnerSetSkipText = "Владелец оставлен без изменений."

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
	"Центр зайдёт на хост ловушки по SSH и сам скачает агент из /downloads/. "
	"Нужны IP, логин, пароль и порт SSH. Это машина, которой ты управляешь. "
	"С хоста ловушки должен быть доступен адрес центра."
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
SetupSshConnectingText = "Центр подключается к {user}@{host}:{port} и ставит агент..."
SetupSshCodeText = "Код с хоста: {code}"
SetupSshFailedText = "Поставить по SSH не вышло: {detail}"
SetupSshManualFallbackText = "Можно поставить вручную командой с карточки."
DeployBadCenterText = (
	"Адрес центра: http(s)://host или host[:port] без кавычек и пробелов "
	"(для агента/курьера - публичный канал, не :8088)."
)

SetupInstallCard = """
+-----------------------------------------------------------+
|  INSTALL CARD                                             |
|  Узел:     {trap_name}
|  Профиль:  {profile_name}
|  Центр:    {api_base}
|                                                           |
|  НА ХОСТЕ ЛОВУШКИ - три команды подряд:                   |
|                                                           |
|  export API_BASE="{api_base}"
|  curl -fsSL -o /tmp/hf-install.sh \\
|    "$API_BASE/downloads/install.sh"
|  sh /tmp/hf-install.sh
|                                                           |
|  Код pairing: pair-confirm <код>
+-----------------------------------------------------------+
"""

SetupCourierInstallCard = """
+-----------------------------------------------------------+
|  COURIER INSTALL CARD                                     |
|  Имя:      {courier_name}
|  Центр:    {api_base}
|                                                           |
|  НА ТРЕТЬЕМ ХОСТЕ (курьер) - три команды подряд:          |
|                                                           |
|  export API_BASE="{api_base}"
|  curl -fsSL -o /tmp/hf-cinst.sh \\
|    "$API_BASE/downloads/install-courier.sh"
|  sh /tmp/hf-cinst.sh
|                                                           |
|  Код: courier-confirm <код> --name {courier_name}
+-----------------------------------------------------------+
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
                               - поставить агент через центр по SSH
  exit | quit                  - выход
  health                       - GET /health
  me                           - текущий пользователь, роль и права
  logout                       - сбросить Bearer-токен

Пользователи и роли (нужны права users.write / roles.write):
  user-list
  user-create --username U --role-id UUID [--password P] [--superadmin]
  user-set-role <user_id> --role-id UUID
  user-disable <user_id> | user-disable <user_id> --enable
  role-list
  role-perms                   - каталог прав
  role-create --name N [--permissions a,b,c]
  role-set-perms <role_id> --permissions a,b,c
  role-delete <role_id>

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
  profile-create --name N --level high --image-token vmi_...
      [--vm-name hf-guest] [--snapshot clean] [--rdp-port 3389]
      [--vm-cpus 2] [--vm-memory-mb 4096] [--no-auto-start]
  profile-update <id> [--file f.json] [--name N] [--description TEXT]
  profile-delete <id>          - удалить профиль
  Уровень: баннер = low, вход/shell/http = medium, emulation VM = high.

Pairing / ловушки:
  pair-list [--status pending|confirmed|completed|expired|all]
  pair-confirm <device_code> [--name trap] [--profile-id UUID]
  traps-list                   - список ловушек и статусы
  trap-show <trap_id>
  trap-bind <trap_id> <profile_id>
  trap-vm start|stop|revert|status|ensure --trap-id UUID
  trap-set-owner <trap_id> --user-id UUID
  trap-set-courier-ssh <trap_id> --host H --user U [--password P] [--port 22]
      [--data-dir /var/lib/metricsd]

Курьер (доставка логов с третьего хоста):
  courier-list
  courier-show <courier_id>
  courier-pair-list [--status pending|...]
  courier-confirm <device_code> [--name courier]
  courier-deploy --host IP --user root [--port 22] [--api-base URL]

События:
  events-list [--trap-id] [--type honeytoken_hit] [--source-ip] [--min-priority high|medium|low] [--limit N]
  events-chains [--trap-id] [--window-sec 3600]
  events-export [--format csv|stix] [-o FILE] [--trap-id] [--type] [--source-ip] [--min-priority] [--since] [--until] [--limit]
  events-tail                  - realtime SSE-лента
  logs-clear [--yes]           - удалить события и журнал аудита
  db-reset [--yes]             - очистить профили, ловушки и логи

Пакеты FS (архив для fake shell, до 32 MiB, zip/tar.gz):
  fs-pack-list
  fs-pack-upload --file PATH [--name N]
  fs-pack-delete TOKEN
  В профиле shell.fs_pack = token (fsp_...) или ubuntu-22.04 / builtin.

Образы VM (OVA для High / VirtualBox, в git не кладём):
  vm-image-list
  vm-image-upload --file PATH.ova [--name N]
  vm-image-delete TOKEN
  В профиле blocks.emulation.image_token = vmi_...
  На хосте ловушки: VirtualBox + VBoxManage.

Personality packs (пресеты banner/HTTP/mask):
  personality-pack-list
  В профиле mask.service_personality = ключ (ubuntu-22.04-ssh, nginx-ops-portal, ...)

При старте CLI: логин и пароль (bootstrap из .env центра: OPERATOR_USERNAME / OPERATOR_PASSWORD).
API_BASE задаётся в .env (по умолчанию http://127.0.0.1:8000).
"""
