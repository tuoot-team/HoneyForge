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
	Write-Host "[build] honeypots -> $OutDir"
	Push-Location $SrcDir
	try {
		$env:GOOS = "windows"
		$env:GOARCH = "amd64"
		$env:CGO_ENABLED = "0"
		go build -mod=vendor -trimpath -ldflags="-s -w" -o (Join-Path $OutDir "agent.exe") ./cmd/agent
	}
	finally {
		Pop-Location
		Remove-Item Env:GOOS -ErrorAction SilentlyContinue
		Remove-Item Env:GOARCH -ErrorAction SilentlyContinue
		Remove-Item Env:CGO_ENABLED -ErrorAction SilentlyContinue
	}
	Publish_Agent (Join-Path $OutDir "agent.exe") (Join-Path $SourceRoot "core-api/downloads/agent.exe")
	Write-Host "[build] honeypots ok: agent.exe"
}

function Publish_Agent([string]$Src, [string]$Dest) {
	New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Dest) | Out-Null
	Copy-Item -Force $Src $Dest
	Write-Host "[build] downloads -> $Dest"
}

Build_Honeypots

Write-Host "[build] готово: $BuildRoot"
Get-ChildItem (Join-Path $BuildRoot "honeypots")
