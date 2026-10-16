#!/bin/bash
# check_mask.sh - проверка что замаскировано в VM
# юзать: ./check_mask.sh Win10-High

VM_NAME="${1:-Win10-High}"

echo "==========================================="
echo " Проверка маскировки домена: $VM_NAME"
echo "==========================================="
echo

echo "[*] CPU:"
sudo virsh --connect qemu:///system dumpxml "$VM_NAME" | grep -A 8 '<cpu ' | grep -E 'model|feature'
echo

echo "[*] SMBIOS:"
sudo virsh --connect qemu:///system dumpxml "$VM_NAME" | grep -A 15 '<sysinfo' | grep -E 'entry name'
echo

echo "[*] MAC-адрес:"
sudo virsh --connect qemu:///system dumpxml "$VM_NAME" | grep 'mac address'
echo

echo "[*] qemu:commandline:"
sudo virsh --connect qemu:///system dumpxml "$VM_NAME" | grep -A 10 'qemu:commandline'
echo

echo "[*] Модель диска (в QEMU):"
sudo virsh --connect qemu:///system dumpxml "$VM_NAME" | grep -A 2 '<target dev=.sda' | grep -E 'bus|model' 
echo

echo "[*] GPU:"
sudo virsh --connect qemu:///system dumpxml "$VM_NAME" | grep -A 3 '<video>'
echo

echo "==========================================="
echo " Чтобы проверить внутри Windows:"
echo "   wmic bios get manufacturer,version,serialnumber"
echo "   wmic computersystem get manufacturer,model"
echo "   wmic diskdrive get model"
echo "   wmic path win32_videocontroller get name"
echo "==========================================="
