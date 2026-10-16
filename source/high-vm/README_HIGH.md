# High-ловушка HoneyForge — Windows 10 в KVM

## Что это

Реализация High-уровня ловушки: реальная Windows 10 Pro в изолированной KVM-VM.
Логирование процессов и PowerShell, honeytokens, откат к чистому состоянию
после каждой сессии атакующего.

## Требования

- Linux-хост (Kali / Debian / Ubuntu)
- KVM + libvirt + virt-install + virt-viewer
- 8+ ГБ RAM, 60+ ГБ диска
- ISO Windows 10 в `/var/lib/libvirt/images/iso/Win10.iso`
- Пользователь в группах `libvirt` и `kvm`

## Установка KVM (если ещё не стоит)

```bash
sudo apt update
sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients \
                    virtinst bridge-utils virt-manager virt-viewer genisoimage
sudo usermod -aG libvirt,kvm $USER
newgrp libvirt
```

Проверка:
```bash
sudo virt-host-validate qemu
```
Все ключевые строки должны быть `OK`.

## Активация сети libvirt

```bash
sudo virsh net-start default
sudo virsh net-autostart default
virsh net-list --all
```
Должно быть `active yes`.

## Шаг 1. Создание VM (без маскировки)

Скачай ISO Windows 10 в `/var/lib/libvirt/images/iso/Win10.iso`.

Создай VM:

```bash
virt-install \
  --connect qemu:///system \
  --name Win10-High \
  --memory 4096 \
  --vcpus 4 \
  --cpu host-passthrough \
  --disk size=60,format=qcow2,bus=sata \
  --cdrom /var/lib/libvirt/images/iso/Win10.iso \
  --network network=default,model=e1000 \
  --graphics vnc,listen=0.0.0.0,port=5901 \
  --os-variant win10 \
  --boot cdrom,hd \
  --noautoconsole
```

Открой консоль:
```bash
virt-viewer --connect qemu:///system Win10-High
```

Установи Windows 10 Pro:
- Язык: Русский
- Редакция: Windows 10 Pro
- Тип установки: Выборочная
- Аккаунт: `user` / пароль `Password123!`
- Сеть в OOBE: пропустить («У меня нет интернета»)
- Конфиденциальность: всё отключить

После установки: Пуск → Завершение работы. VM должна быть `shut off`.

## Шаг 2. Применение маскировки

Скопируй `xml/win10-masked.xml` из архива в `/tmp/` и примени:

```bash
sudo virsh --connect qemu:///system define /tmp/win10-masked.xml
```

Скопируй скрипты из `scripts/` в `~/scripts/`:

```bash
mkdir -p ~/scripts
cp scripts/*.sh ~/scripts/
chmod +x ~/scripts/*.sh
```

Запусти VM через скрипт:

```bash
~/scripts/start_vm.sh Win10-High
```

Проверь маскировку:

```bash
~/scripts/check_mask.sh Win10-High
```

Внутри Windows проверь:
```
wmic bios get manufacturer,version,serialnumber
wmic computersystem get manufacturer,model
```
Ожидается:
```
Manufacturer: American Megatrends Inc.
SerialNumber: BASEBOARD_SERIAL
Version:      F31o

Manufacturer: Gigabyte Technology Co., Ltd.
Model:        X570 AORUS ULTRA
```

## Шаг 3. Логирование внутри Windows

Открой PowerShell от администратора (Win+X → PowerShell администратор).

Включи Script Block Logging:
```powershell
reg add HKLM\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging /v EnableScriptBlockLogging /t REG_DWORD /d 1 /f
```

Включи Module Logging:
```powershell
reg add HKLM\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ModuleLogging /v EnableModuleLogging /t REG_DWORD /d 1 /f
```

Включи аудит создания процессов (для русской Windows — название на русском):
```powershell
auditpol /set /subcategory:"Создание процесса" /success:enable /failure:enable
```

## Шаг 4. Honeytokens

В том же PowerShell:

```powershell
mkdir C:\Users\user\Documents\Backup
echo admin:Winter2024! > C:\Users\user\Documents\passwords.txt
echo DB_PASSWORD=SuperSecret2024 > C:\Users\user\Documents\.env.bak
echo AWS_KEY=AKIAFAKE1234567890 > C:\Users\user\Documents\aws_credentials.csv
mkdir C:\Users\user\.ssh
echo -----BEGIN OPENSSH PRIVATE KEY----- > C:\Users\user\.ssh\id_rsa
echo FAKEKEYFORANALYSISPURPOSESONLY >> C:\Users\user\.ssh\id_rsa
echo -----END OPENSSH PRIVATE KEY----- >> C:\Users\user\.ssh\id_rsa
```

Проверка:
```powershell
dir C:\Users\user\Documents\
```
Должно быть 3 файла + Backup.

## Шаг 5. Snapshot (точка отката)

Выключи Windows: Пуск → Завершение работы.

В Linux-хосте:

```bash
virsh --connect qemu:///system snapshot-create-as Win10-High clean-final \
    "clean state with honeytokens" --disk-only --atomic
virsh --connect qemu:///system start Win10-High
```

Проверка:
```bash
virsh --connect qemu:///system snapshot-list Win10-High
```
Должен быть `clean-final` в состоянии `disk-snapshot`.

## Шаг 6. Тест сквозного сценария

Запусти VM:
```bash
~/scripts/start_vm.sh Win10-High
```

Внутри Windows открой PowerShell (простой) и имитируй атаку:
```powershell
whoami
dir C:\Users
type C:\Users\user\Documents\passwords.txt
```

Проверь логи в админском PowerShell:
```powershell
Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4688} -MaxEvents 5 | Format-Table TimeCreated -AutoSize
```

Должны быть свежие timestamp — события только что записались.

## Откат после сессии атакующего

```bash
~/scripts/reset_vm.sh Win10-High
```

VM вернётся к чистому состоянию `clean-final`. Все следы предыдущей сессии стираются.

## Состав архива

```
honeyforge_submit/
├── README_HIGH.md               # этот файл
├── scripts/
│   ├── apply_mask.sh            # маскировка CPUID/SMBIOS/MAC
│   ├── check_mask.sh            # проверка маскировки
│   ├── start_vm.sh              # запуск VM + консоль
│   └── reset_vm.sh              # откат к clean-final
└── xml/
    └── win10-masked.xml         # XML-конфиг с маскировкой
```

## Известные ограничения

- BIOS version в `wmic` показывает `BOCHS - 1` (не критично, слабый сигнал детекта).
- Модель диска — `QEMU HARDDISK` (не критично).
- GPU — Standard VGA (не критично).
- Отправка событий в core-api не реализована в этом архиве.
  События пишутся в локальный Security Event Log (ID 4688, 4104).
  Для отправки в центр — дописать скрипт `sender.ps1` (см. отдельно).
