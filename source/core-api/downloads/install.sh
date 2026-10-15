#!/bin/sh
# Ставит агент из /downloads/ центра и запускает pairing.
# Не пайпить в sh (curl error 23). Скачай файл, потом:
#   export API_BASE=https://example.com
#   curl -fsSL -o /tmp/hf-install.sh "$API_BASE/downloads/install.sh"
#   sh /tmp/hf-install.sh
# HF_NO_START=1 только скачивает. HF_INSTALL_DIR задаёт каталог.
set -eu

msg_NeedCenter="Нужен адрес центра.
  export API_BASE=https://example.com
  curl -fsSL -o /tmp/hf-install.sh \"\$API_BASE/downloads/install.sh\"
  sh /tmp/hf-install.sh
  # или: sh install.sh https://example.com"
msg_NeedArch="В /downloads/ лежит агент linux/amd64. Эта машина: "
msg_NeedFetch="Нужен curl или wget, чтобы скачать агент."
msg_Downloading="Скачиваю агент: "
msg_Installed="Агент установлен в "
msg_Next="Дальше агент запросит код. Подтверди его в CLI: pair-confirm <код>"
msg_HighVm="High VM: на этом хосте нужны VirtualBox и VBoxManage в PATH."
msg_ManualStart="Запуск вручную: "

center="${API_BASE:-}"
if [ -z "$center" ] && [ "${1:-}" != "" ]; then
	center="$1"
fi
center="${center%/}"
if [ -z "$center" ]; then
	echo "$msg_NeedCenter" >&2
	exit 1
fi

arch="$(uname -m)"
case "$arch" in
	x86_64|amd64) ;;
	*)
		echo "${msg_NeedArch}${arch}" >&2
		exit 1
		;;
esac

if [ "$(id -u)" -eq 0 ]; then
	dest="/var/lib/metricsd"
else
	dest="${HOME}/.local/share/metricsd"
fi
if [ -n "${HF_INSTALL_DIR:-}" ]; then
	dest="$HF_INSTALL_DIR"
fi
mkdir -p "$dest"

# Центр отдаёт /downloads/agent; на диске - нейтральное имя.
agent_url="${center}/downloads/agent"
agent_path="${dest}/metricsd"
echo "${msg_Downloading}${agent_url}"
tmp_path="${agent_path}.tmp.$$"
if command -v curl >/dev/null 2>&1; then
	curl -fsSL --connect-timeout 20 --max-time 300 --retry 3 --retry-delay 2 \
		"$agent_url" -o "$tmp_path"
elif command -v wget >/dev/null 2>&1; then
	wget -q -T 300 -O "$tmp_path" "$agent_url"
else
	echo "$msg_NeedFetch" >&2
	exit 1
fi
if [ ! -s "$tmp_path" ]; then
	rm -f "$tmp_path"
	echo "Пустой бинарь - проверь $agent_url" >&2
	exit 1
fi
mv -f "$tmp_path" "$agent_path"
chmod +x "$agent_path"

{
	echo "API_BASE=${center}"
	echo "DEBUG=false"
	# Опциональный mTLS: задайте TLS_CLIENT_* при установке или допишите в .env вручную.
	if [ -n "${TLS_CLIENT_CERT:-}" ] && [ -n "${TLS_CLIENT_KEY:-}" ]; then
		echo "TLS_CLIENT_CERT=${TLS_CLIENT_CERT}"
		echo "TLS_CLIENT_KEY=${TLS_CLIENT_KEY}"
	fi
	if [ -n "${TLS_CA:-}" ]; then
		echo "TLS_CA=${TLS_CA}"
	fi
} > "${dest}/.env"

echo "${msg_Installed}${dest}"
echo "$msg_Next"
echo "$msg_HighVm"
if [ "${HF_NO_START:-}" = "1" ]; then
	echo "${msg_ManualStart}${agent_path}"
	exit 0
fi

cd "$dest"
exec "$agent_path"
