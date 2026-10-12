//go:build linux

package agent

import (
	"syscall"
	"unsafe"
)

const prSetName = 15

// Set_ProcessName меняет имя процесса в ps (до 15 байт).
func Set_ProcessName(name string) {
	if name == "" {
		return
	}
	b := make([]byte, 16)
	copy(b, name)
	_, _, _ = syscall.RawSyscall(syscall.SYS_PRCTL, prSetName, uintptr(unsafe.Pointer(&b[0])), 0)
}
