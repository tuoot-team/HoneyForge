#!/bin/sh
# Проверка inbox после поставки образа. VM не запускает.
set -eu

root="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
inbox="${root}/inbox"
manifests="${root}/manifests"

echo "== high-vm intake =="
echo "inbox:     $inbox"
echo "manifests: $manifests"

if [ ! -d "$inbox" ]; then
	echo "нет каталога inbox - создайте и положите OVA/VDI" >&2
	exit 1
fi

count=0
for f in "$inbox"/*; do
	[ -e "$f" ] || continue
	case "$(basename "$f")" in
		.gitkeep|README*) continue ;;
	esac
	count=$((count + 1))
	sz="$(wc -c < "$f" | tr -d ' ')"
	echo "  file: $(basename "$f")  bytes=$sz"
	if command -v sha256sum >/dev/null 2>&1; then
		sha256sum "$f" | awk '{print "  sha256: "$1}'
	fi
done

if [ "$count" -eq 0 ]; then
	echo "inbox пуст - ждём поставку от Кирилла" >&2
	exit 2
fi

echo "манифесты:"
found_m=0
for f in "$manifests"/*.md; do
	[ -e "$f" ] || continue
	base="$(basename "$f")"
	[ "$base" = "TEMPLATE.md" ] && continue
	echo "  $base"
	found_m=1
done
if [ "$found_m" -eq 0 ]; then
	echo "  (нет заполненного манифеста - скопируйте TEMPLATE.md)" >&2
fi

echo
echo "дальше: smoke VBoxManage → vm-image-upload → profile high / см. INTAKE.md"
