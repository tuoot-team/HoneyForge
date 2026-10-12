#!/usr/bin/env bash
# Сборка Linux-артефактов всего проекта в build/<модуль>/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_ROOT="${ROOT}/build"
SOURCE_ROOT="${ROOT}/source"

echo "[build] root=${ROOT}"
mkdir -p "${BUILD_ROOT}"

build_Honeypots() {
	local out_dir="${BUILD_ROOT}/honeypots"
	local src_dir="${SOURCE_ROOT}/honeypots"
	mkdir -p "${out_dir}"
	echo "[build] honeypots -> ${out_dir}"
	(
		cd "${src_dir}"
		# -mod=vendor: без сети; CGO=0: статический бинарь (не требует новый glibc на цели)
		CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -mod=vendor -trimpath -ldflags="-s -w" -o "${out_dir}/agent" ./cmd/agent
	)
	publish_Agent "${out_dir}/agent" "${SOURCE_ROOT}/core-api/downloads/agent"
	echo "[build] honeypots ok: agent"
}

# Бинарь, который центр отдаёт хосту ловушки.
publish_Agent() {
	local src="$1"
	local dest="$2"
	mkdir -p "$(dirname "${dest}")"
	cp "${src}" "${dest}"
	chmod +x "${dest}"
	echo "[build] downloads -> ${dest}"
}

build_Honeypots

echo "[build] готово: ${BUILD_ROOT}"
ls -la "${BUILD_ROOT}/honeypots"
