# Чеклист приёмки VM (оператор HoneyForge)

Когда Кирилл скинул образ:

1. **Положить файлы** в `source/high-vm/inbox/` (не коммитить).
2. **Скопировать манифест** из его описания в `manifests/<имя>.md` по [`TEMPLATE.md`](manifests/TEMPLATE.md).
3. **Проверить целостность** (если есть sha256):
   ```bash
   sha256sum inbox/*.ova
   ```
4. **Smoke на стенде** (VirtualBox, не прод):
   ```bash
   VBoxManage import inbox/<name>.ova --vsys 0 --vmname hf-high-intake
   VBoxManage startvm hf-high-intake --type headless
   ```
5. **Smoke гостя**:
   - boot до логина
   - RDP/SSH с хоста стенда
   - известная учётка работает
   - зафиксировать время boot и «палево» глазами
6. **Записать результат** в манифест: OK / блокеры.
7. **В продукт**:
   - `vm-image-upload --file inbox/<name>.ova` → token `vmi_…`
   - `profile-create --name … --level high --image-token vmi_…` (или setup high)
   - на ловушке: VirtualBox + `VBoxManage`, обычный deploy агента
   - `trap-bind` / `trap-vm start|stop|revert|status`

KVM/libvirt и sleep/wake proxy - вне текущего MVP (см. README).

Скрипт-заготовка: [`scripts/intake_check.sh`](scripts/intake_check.sh).
