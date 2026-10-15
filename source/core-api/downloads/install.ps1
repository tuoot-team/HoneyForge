# Ставит Windows-агент из /downloads/ центра и запускает pairing.
#   $env:API_BASE='http://127.0.0.1:8000'; irm "$env:API_BASE/downloads/install.ps1" | iex
#   ./install.ps1 http://127.0.0.1:8000
# HF_NO_START=1 только скачивает. HF_INSTALL_DIR задаёт каталог.
# Сначала останавливает прошлую установку, потом качает бинарь.
$ErrorActionPreference = "Stop"

$MsgPrevNone = "Прошлой установки нет."
$MsgPrevFound = "Нашёл прошлую установку, останавливаю: "

function Stop-PreviousInstall {
	param(
		[string]$Dest,
		[string]$BinaryName,
		[string]$BinaryPath
	)
	$pidFile = Join-Path $Dest "daemon.pid"
	$runtimeFile = Join-Path $Dest ".runtime.json"
	$logFile = Join-Path $Dest "daemon.log"
	$hadPid = Test-Path $pidFile
	$hadRuntime = Test-Path $runtimeFile
	$hadBinary = Test-Path $BinaryPath
	if (-not ($hadPid -or $hadRuntime -or $hadBinary)) {
		Write-Host $MsgPrevNone
		return
	}
	Write-Host "$MsgPrevFound$Dest"
	$fullBinary = [System.IO.Path]::GetFullPath($BinaryPath)
	$processIds = @()
	if ($hadPid) {
		foreach ($line in @(Get-Content $pidFile -ErrorAction SilentlyContinue)) {
			$id = 0
			if ([int]::TryParse("$line".Trim(), [ref]$id) -and $id -gt 0) {
				$processIds += $id
			}
		}
	}
	# Имя процесса может не совпасть с exe, поэтому сверяем полный путь.
	try {
		$listed = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
		foreach ($proc in @($listed)) {
			if (-not $proc.ExecutablePath) {
				continue
			}
			$fullExe = [System.IO.Path]::GetFullPath($proc.ExecutablePath)
			if ($fullExe -ieq $fullBinary) {
				$processIds += [int]$proc.ProcessId
			}
		}
	} catch {
	}
	$processIds = @($processIds | Select-Object -Unique)
	foreach ($id in $processIds) {
		Stop-Process -Id $id -ErrorAction SilentlyContinue
	}
	if ($processIds.Count -gt 0) {
		Start-Sleep -Seconds 1
		foreach ($id in $processIds) {
			Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
		}
	}
	Get-Process -Name $BinaryName -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
	if ($hadRuntime) {
		Remove-Item -Force $runtimeFile -ErrorAction SilentlyContinue
	}
	if ($hadPid) {
		Remove-Item -Force $pidFile -ErrorAction SilentlyContinue
	}
	if (Test-Path $logFile) {
		Clear-Content $logFile -ErrorAction SilentlyContinue
	}
}

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
$dest = [System.IO.Path]::GetFullPath($dest)

$agentUrl = "$center/downloads/agent.exe"
$agentPath = Join-Path $dest "metricsd.exe"
Stop-PreviousInstall -Dest $dest -BinaryName "metricsd" -BinaryPath $agentPath
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
