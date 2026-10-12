$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BuildRoot = Join-Path $Root "build"
$SourceRoot = Join-Path $Root "source"

Write-Host "[build] root=$Root"
New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null

function Build_Honeypots {
	$OutDir = Join-Path $BuildRoot "honeypots"
	$SrcDir = Join-Path $SourceRoot "honeypots"
	New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
	Write-Host "[build] honeypots (linux/amd64) -> $OutDir"
	Push-Location $SrcDir
	try {
		$env:GOOS = "linux"
		$env:GOARCH = "amd64"
		# CGO=0: статический бинарь (не требует новый glibc на цели)
		$env:CGO_ENABLED = "0"
		go build -mod=vendor -trimpath -ldflags="-s -w" -o (Join-Path $OutDir "agent") ./cmd/agent
	}
	finally {
		Pop-Location
		Remove-Item Env:GOOS -ErrorAction SilentlyContinue
		Remove-Item Env:GOARCH -ErrorAction SilentlyContinue
		Remove-Item Env:CGO_ENABLED -ErrorAction SilentlyContinue
	}
	Publish_Agent (Join-Path $OutDir "agent") (Join-Path $SourceRoot "core-api/downloads/agent")
	Write-Host "[build] honeypots ok: agent"
}

function Publish_Agent([string]$Src, [string]$Dest) {
	New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Dest) | Out-Null
	Copy-Item -Force $Src $Dest
	Write-Host "[build] downloads -> $Dest"
}

function Pack_CoreApi([string]$AgentSrc, [string]$AgentName) {
	$Stage = Join-Path $BuildRoot "core-api"
	$Archive = Join-Path $BuildRoot "core-api.tar.gz"
	$Src = Join-Path $SourceRoot "core-api"
	if (Test-Path $Stage) {
		Remove-Item -Recurse -Force $Stage
	}
	Write-Host "[build] core-api -> $Stage"
	Copy-Item -Recurse -Force $Src $Stage
	Get-ChildItem -Path $Stage -Recurse -Force -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
	Get-ChildItem -Path $Stage -Recurse -Force -File -Include *.pyc,honeyforge_local.db | Remove-Item -Force
	Get-ChildItem -Path $Stage -Recurse -Force -File -Filter .env | Remove-Item -Force
	Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $Stage "downloads/agent")
	Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $Stage "downloads/agent.exe")
	New-Item -ItemType Directory -Force -Path (Join-Path $Stage "downloads") | Out-Null
	Copy-Item -Force $AgentSrc (Join-Path $Stage "downloads/$AgentName")
	if (Test-Path $Archive) {
		Remove-Item -Force $Archive
	}
	Write-Host "[build] archive -> $Archive"
	tar -C $BuildRoot -czf $Archive core-api
	Remove-Item -Recurse -Force $Stage
}

Build_Honeypots
Pack_CoreApi (Join-Path $BuildRoot "honeypots/agent") "agent"

Write-Host "[build] готово: $BuildRoot"
Get-ChildItem (Join-Path $BuildRoot "honeypots")
Get-Item (Join-Path $BuildRoot "core-api.tar.gz")
