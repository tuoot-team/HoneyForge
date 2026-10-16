#!/bin/bash
# start_vm.sh - запуск VM + консоль
VM_NAME="${1:-Win10-High}"

echo "[*] Запускаю VM $VM_NAME..."
virsh --connect qemu:///system start "$VM_NAME" 2>/dev/null || echo "Уже запущена"

echo "[*] Открываю консоль..."
virt-viewer --connect qemu:///system "$VM_NAME"
