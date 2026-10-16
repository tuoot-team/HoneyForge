#!/bin/bash
# apply_mask.sh - маскировка KVM домена под обычный физический пк
# запускать при выключенной VM, иначе изменения не применятся
# юзать: ./apply_mask.sh Win10-High

set -e

VM_NAME="$1"

if [ -z "$VM_NAME" ]; then
    echo "Использование: $0 <имя_домена>"
    exit 1
fi

echo "[*] Маскирую домен '$VM_NAME'..."

# 1. CPU - скрываем бит гипервизора и подменяем модель
sudo virt-xml "$VM_NAME" --connect qemu:///system --edit --cpu host-passthrough,model=Skylake-Client-IBRS

# скрываем KVM и бит гипервизора через отдельные опции
sudo virt-xml "$VM_NAME" --connect qemu:///system --edit --cpu host-passthrough,feature=vmx=off
sudo virt-xml "$VM_NAME" --connect qemu:///system --edit --cpu host-passthrough,feature=hypervisor=off

# 2. SMBIOS - под гигабайт x570
sudo virt-xml "$VM_NAME" --connect qemu:///system --edit --sysinfo type=smbios \
    bios.vendor='American Megatrends Inc.',bios.version='F31o',bios.date='12/03/2020' \
    system.manufacturer='Gigabyte Technology Co., Ltd.',system.product='X570 AORUS ULTRA' \
    system.version='x.x',system.serial='BASEBOARD_SERIAL',system.sku='BASEBOARD_SKU',system.family='X570 MB'

# 3. включаем режим sysinfo чтобы smbios применился
sudo virt-xml "$VM_NAME" --connect qemu:///system --edit --os smbios.mode=sysinfo

# 4. MAC - префикс интела, хвост рандомный
RAND_MAC=$(printf '00:1B:21:%02X:%02X:%02X' $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)))
sudo virt-xml "$VM_NAME" --connect qemu:///system --edit --network mac.address="$RAND_MAC"
echo "[+] MAC: $RAND_MAC"

echo "[+] Готово. Запускай VM: virsh start '$VM_NAME'"
