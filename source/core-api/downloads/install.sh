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
msg_PrevNone="Прошлой установки нет."
msg_PrevFound="Нашёл прошлую установку, останавливаю: "

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
dest=$(CDPATH= cd "$dest" && pwd -P)

# comm после маски процесса не совпадает с именем бинаря, поэтому ищем по exe.
stop_Previous() {
	bin_name="$1"
	bin_path="$2"
	pid_file="${dest}/daemon.pid"
	runtime_file="${dest}/.runtime.json"
	log_file="${dest}/daemon.log"
	if [ ! -f "$bin_path" ] && [ ! -f "$pid_file" ] && [ ! -f "$runtime_file" ]; then
		echo "$msg_PrevNone"
		return 0
	fi
	echo "${msg_PrevFound}${dest}"
	bin_real=$(readlink -f "$bin_path" 2>/dev/null || echo "$bin_path")
	pids=""
	if [ -f "$pid_file" ]; then
		pid=$(tr -cd '0-9' < "$pid_file" || true)
		if [ -n "$pid" ]; then
			pids="$pids $pid"
		fi
	fi
	for exe in /proc/[0-9]*/exe; do
		[ -e "$exe" ] || continue
		exe_link=$(readlink "$exe" 2>/dev/null || true)
		exe_link=${exe_link% (deleted)}
		exe_real=$(readlink -f "$exe" 2>/dev/null || true)
		exe_real=${exe_real% (deleted)}
		if [ -n "$bin_real" ] && { [ "$exe_link" = "$bin_path" ] || [ "$exe_link" = "$bin_real" ] || [ "$exe_real" = "$bin_real" ]; }; then
			pid=${exe#/proc/}
			pid=${pid%/exe}
			pids="$pids $pid"
		fi
	done
	sent=0
	for pid in $pids; do
		if [ "$pid" -eq 0 ] || [ "$pid" -eq 1 ] || [ "$pid" -eq "$$" ]; then
			continue
		fi
		kill -TERM "$pid" 2>/dev/null || true
		sent=1
	done
	if [ "$sent" -eq 1 ]; then
		sleep 1
	fi
	for pid in $pids; do
		if [ "$pid" -eq 0 ] || [ "$pid" -eq 1 ] || [ "$pid" -eq "$$" ]; then
			continue
		fi
		kill -KILL "$pid" 2>/dev/null || true
	done
	pkill -KILL -x "$bin_name" 2>/dev/null || true
	rm -f "$runtime_file" "$pid_file"
	if [ -f "$log_file" ]; then
		: > "$log_file"
	fi
}

# Центр отдаёт /downloads/agent; на диске - нейтральное имя.
agent_url="${center}/downloads/agent"
agent_path="${dest}/metricsd"
stop_Previous metricsd "$agent_path"
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
