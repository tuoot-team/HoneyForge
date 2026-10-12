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
	echo "[build] honeypots (windows/amd64) -> ${out_dir}"
	(
		cd "${src_dir}"
		CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -mod=vendor -trimpath -ldflags="-s -w" -o "${out_dir}/agent.exe" ./cmd/agent
	)
	publish_Agent "${out_dir}/agent.exe" "${SOURCE_ROOT}/core-api/downloads/agent.exe"
	echo "[build] honeypots ok: agent.exe"
}

publish_Agent() {
	local src="$1"
	local dest="$2"
	mkdir -p "$(dirname "${dest}")"
	cp "${src}" "${dest}"
	echo "[build] downloads -> ${dest}"
}

pack_CoreApi() {
	local agent_src="$1"
	local agent_name="$2"
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
		-cf - . | tar -C "${stage}" -xf -
	mkdir -p "${stage}/downloads"
	cp "${agent_src}" "${stage}/downloads/${agent_name}"
	find "${stage}" -type d -name '__pycache__' -prune -exec rm -rf {} +
	find "${stage}" -type f \( -name '*.pyc' -o -name '.env' -o -name 'honeyforge_local.db' \) -delete
	echo "[build] archive -> ${archive}"
	rm -f "${archive}"
	tar -C "${BUILD_ROOT}" -czf "${archive}" core-api
	rm -rf "${stage}"
}

build_Honeypots
pack_CoreApi "${BUILD_ROOT}/honeypots/agent.exe" "agent.exe"

echo "[build] готово: ${BUILD_ROOT}"
ls -la "${BUILD_ROOT}/honeypots" "${BUILD_ROOT}/core-api.tar.gz"
