#!/bin/bash
# reset_vm.sh - откат VM к чистому snapshot
VM_NAME="${1:-Win10-High}"

echo "[*] Останавливаю VM..."
virsh --connect qemu:///system destroy "$VM_NAME" 2>/dev/null || true

echo "[*] Откатываю к clean-state..."
virsh --connect qemu:///system snapshot-revert "$VM_NAME" clean-final

echo "[*] Запускаю заново..."
virsh --connect qemu:///system start "$VM_NAME"

echo "[+] Готово."
