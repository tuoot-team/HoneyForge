# Фаза 6b - High VM (VirtualBox)

Продуктовый путь: образ в реестре центра → `profile.blocks.emulation` → агент на ловушке через `VBoxManage`.

Inbox в этом каталоге остаётся складом артефактов до upload.

## Путь оператора

1. Принять OVA от Кирилла в `inbox/` + манифест (`INTAKE.md`, `manifests/TEMPLATE.md`).
2. Загрузить в центр: `vm-image-upload --file path/to/disk.ova` → token `vmi_…`.
3. Профиль high:
   - setup (вопрос High VirtualBox VM), или
   - `profile-create --name N --level high --image-token vmi_… [--rdp-port 3389]`
4. На хосте ловушки: **VirtualBox** + `VBoxManage` в PATH; обычный `deploy` / install.sh.
5. `trap-bind` ставит в очередь `vm_ensure` (+ `vm_start` если `auto_start`).
6. Управление: `trap-vm start|stop|revert|status|ensure --trap-id UUID`.

## Блок emulation

```json
"emulation": {
  "enabled": true,
  "runtime": "virtualbox",
  "image_token": "vmi_…",
  "vm_name": "hf-trap-1",
  "cpus": 2,
  "memory_mb": 4096,
  "snapshot": "clean",
  "expose": [{"host_port": 3389, "guest_port": 3389, "proto": "tcp"}],
  "auto_start": true
}
```

Уровень `interaction_level=high` допустим только при `emulation.enabled` и существующем `image_token`.

## События

Агент шлёт `vm_ensure` / `vm_start` / `vm_stop` / `vm_revert` / `vm_status` с payload `{vm_name, ok, detail}`.

## Вне этого среза

KVM/libvirt, sleep+wake RDP proxy, полный антидетект, in-guest Windows agent.

## Приёмка образа

См. [`INTAKE.md`](INTAKE.md), текст для Кирилла [`KIRILL.md`](KIRILL.md).
