#!/bin/sh
# Ставит курьера из /downloads/ центра.
# Не пайпить в sh (curl error 23):
#   export API_BASE=https://example.com
#   curl -fsSL -o /tmp/hf-cinst.sh "$API_BASE/downloads/install-courier.sh"
#   sh /tmp/hf-cinst.sh
set -eu

msg_NeedCenter="Нужен адрес центра.
  export API_BASE=https://example.com
  curl -fsSL -o /tmp/hf-cinst.sh \"\$API_BASE/downloads/install-courier.sh\"
  sh /tmp/hf-cinst.sh"
msg_NeedArch="В /downloads/ лежит courier linux/amd64. Эта машина: "
msg_NeedFetch="Нужен curl или wget."
msg_Downloading="Скачиваю курьера: "
msg_Installed="Курьер установлен в "
msg_Next="Дальше курьер запросит код. Подтверди: courier-confirm <код>"
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
	dest="/var/lib/metricsd-relay"
else
	dest="${HOME}/.local/share/metricsd-relay"
fi
if [ -n "${HF_INSTALL_DIR:-}" ]; then
	dest="$HF_INSTALL_DIR"
fi
mkdir -p "$dest"

# Центр отдаёт /downloads/courier; на диске - нейтральное имя.
bin_url="${center}/downloads/courier"
bin_path="${dest}/metricsd-relay"
echo "${msg_Downloading}${bin_url}"
tmp_path="${bin_path}.tmp.$$"
if command -v curl >/dev/null 2>&1; then
	curl -fsSL --connect-timeout 20 --max-time 300 --retry 3 --retry-delay 2 \
		"$bin_url" -o "$tmp_path"
elif command -v wget >/dev/null 2>&1; then
	wget -q -T 300 -O "$tmp_path" "$bin_url"
else
	echo "$msg_NeedFetch" >&2
	exit 1
fi
if [ ! -s "$tmp_path" ]; then
	rm -f "$tmp_path"
	echo "Пустой бинарь - проверь $bin_url" >&2
	exit 1
fi
mv -f "$tmp_path" "$bin_path"
chmod +x "$bin_path"

cat > "${dest}/.env" <<EOF
API_BASE=${center}
DEBUG=false
EOF

echo "${msg_Installed}${dest}"
echo "$msg_Next"
if [ "${HF_NO_START:-}" = "1" ]; then
	echo "${msg_ManualStart}${bin_path}"
	exit 0
fi

cd "$dest"
exec "$bin_path"
