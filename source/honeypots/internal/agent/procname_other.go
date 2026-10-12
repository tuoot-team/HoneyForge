//go:build !linux

package agent

func Set_ProcessName(name string) {
	_ = name
}
