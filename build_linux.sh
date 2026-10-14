#!/usr/bin/env bash
# Сборка Linux-артефактов всего проекта в build/<модуль>/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_ROOT="${ROOT}/build"
SOURCE_ROOT="${ROOT}/source"

echo "[build] root=${ROOT}"
mkdir -p "${BUILD_ROOT}"

# Бинарь в downloads/ центра (статический, без привязки к glibc на цели).
publish_Bin() {
	local src="$1"
	local dest="$2"
	mkdir -p "$(dirname "${dest}")"
	cp "${src}" "${dest}"
	chmod +x "${dest}"
	echo "[build] downloads -> ${dest}"
}

build_Honeypots() {
	local out_dir="${BUILD_ROOT}/honeypots"
	local src_dir="${SOURCE_ROOT}/honeypots"
	mkdir -p "${out_dir}"
	echo "[build] honeypots -> ${out_dir}"
	(
		cd "${src_dir}"
		# -mod=vendor: без сети; CGO=0: статический бинарь (не требует новый glibc на цели)
		CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -mod=vendor -trimpath -ldflags="-s -w" \
			-o "${out_dir}/agent" ./cmd/agent
		CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -mod=vendor -trimpath -ldflags="-s -w" \
			-o "${out_dir}/courier" ./cmd/courier
	)
	publish_Bin "${out_dir}/agent" "${SOURCE_ROOT}/core-api/downloads/agent"
	publish_Bin "${out_dir}/courier" "${SOURCE_ROOT}/core-api/downloads/courier"
	echo "[build] honeypots ok: agent + courier"
}

# Кэш, локальная БД и .env в архив центра не входят.
pack_CoreApi() {
	local stage="${BUILD_ROOT}/core-api"
	local archive="${BUILD_ROOT}/core-api.tar.gz"
	echo "[build] core-api -> ${stage}"
	rm -rf "${stage}"
	mkdir -p "${stage}"
	tar -C "${SOURCE_ROOT}/core-api" \
		--exclude='.env' \
		--exclude='__pycache__' \
		--exclude='*.pyc' \
		--exclude='honeyforge_local.db' \
		--exclude='.venv' \
		--exclude='venv' \
		--exclude='downloads/agent' \
		--exclude='downloads/agent.exe' \
		--exclude='downloads/courier' \
		-cf - . | tar -C "${stage}" -xf -
	mkdir -p "${stage}/downloads"
	cp "${BUILD_ROOT}/honeypots/agent" "${stage}/downloads/agent"
	cp "${BUILD_ROOT}/honeypots/courier" "${stage}/downloads/courier"
	chmod +x "${stage}/downloads/agent" "${stage}/downloads/courier"
	find "${stage}" -type d -name '__pycache__' -prune -exec rm -rf {} +
	find "${stage}" -type f \( -name '*.pyc' -o -name '.env' -o -name 'honeyforge_local.db' \) -delete
	echo "[build] archive -> ${archive}"
	rm -f "${archive}"
	tar -C "${BUILD_ROOT}" -czf "${archive}" core-api
	rm -rf "${stage}"
}

build_Honeypots
pack_CoreApi

echo "[build] готово: ${BUILD_ROOT}"
ls -la "${BUILD_ROOT}/honeypots" "${BUILD_ROOT}/core-api.tar.gz"
file "${BUILD_ROOT}/honeypots/agent" "${BUILD_ROOT}/honeypots/courier"
