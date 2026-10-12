package config

import (
	"os"
	"path/filepath"
	"strings"
)

const (
	DefaultBaseURL = "http://127.0.0.1:8000"
	AgentVersion   = "0.1.0"
)

func Load_DotEnv(honeypotsRoot string) {
	load_EnvFile(filepath.Join(honeypotsRoot, ".env"))
	parent := filepath.Dir(honeypotsRoot)
	load_EnvFile(filepath.Join(parent, "cli", ".env"))
	load_EnvFile(filepath.Join(parent, "core-api", ".env"))
}

func Is_Debug() bool {
	v := strings.ToLower(strings.TrimSpace(os.Getenv("DEBUG")))
	return v == "1" || v == "true" || v == "yes"
}

func Get_BaseUrl() string {
	base := strings.TrimSpace(os.Getenv("API_BASE"))
	if base == "" {
		base = DefaultBaseURL
	}
	return strings.TrimRight(base, "/")
}

// Get_DataDir: в репо (есть go.mod) - корень модуля; у задеплоенного бинаря - папка рядом с ним.
func Get_DataDir(honeypotsRoot string) string {
	if _, err := os.Stat(filepath.Join(honeypotsRoot, "go.mod")); err == nil {
		return honeypotsRoot
	}
	if exe, err := os.Executable(); err == nil {
		return filepath.Dir(exe)
	}
	return honeypotsRoot
}

func Get_StatePath(honeypotsRoot string) string {
	if envPath := strings.TrimSpace(os.Getenv("AGENT_STATE")); envPath != "" {
		return envPath
	}
	return filepath.Join(Get_DataDir(honeypotsRoot), ".agent_state.json")
}

func Get_BufferPath(honeypotsRoot string) string {
	if envPath := strings.TrimSpace(os.Getenv("EVENTS_BUFFER")); envPath != "" {
		return envPath
	}
	return filepath.Join(Get_DataDir(honeypotsRoot), "events_buffer.json")
}

func Debug_Log(debug bool, message string) {
	if debug {
		println("[DEBUG]", message)
	}
}
