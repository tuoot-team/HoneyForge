# Ставит Windows-агент из /downloads/ центра и запускает pairing.
#   $env:API_BASE='http://127.0.0.1:8000'; irm "$env:API_BASE/downloads/install.ps1" | iex
#   ./install.ps1 http://127.0.0.1:8000
# HF_NO_START=1 только скачивает. HF_INSTALL_DIR задаёт каталог.
$ErrorActionPreference = "Stop"

$center = $env:API_BASE
if (-not $center -and $args.Count -ge 1) {
	$center = $args[0]
}
if ($center) {
	$center = $center.TrimEnd("/")
}
if (-not $center) {
	Write-Host "Нужен адрес центра."
	Write-Host "  `$env:API_BASE='http://127.0.0.1:8000'; irm `"`$env:API_BASE/downloads/install.ps1`" | iex"
	exit 1
}

if ($env:HF_INSTALL_DIR) {
	$dest = $env:HF_INSTALL_DIR
} else {
	$dest = Join-Path $env:USERPROFILE ".local\share\metricsd"
}
New-Item -ItemType Directory -Force -Path $dest | Out-Null

$agentUrl = "$center/downloads/agent.exe"
$agentPath = Join-Path $dest "metricsd.exe"
Write-Host "Скачиваю агент: $agentUrl"
Invoke-WebRequest -Uri $agentUrl -OutFile $agentPath

@(
	"API_BASE=$center"
	"DEBUG=false"
) | Set-Content -Path (Join-Path $dest ".env") -Encoding ascii

Write-Host "Агент установлен в $dest"
Write-Host "Дальше агент запросит код. Подтверди его в CLI: pair-confirm <код>"
if ($env:HF_NO_START -eq "1") {
	Write-Host "Запуск вручную: $agentPath"
	exit 0
}

Set-Location $dest
& $agentPath
