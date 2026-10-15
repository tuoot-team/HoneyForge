package vm

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"

	"metricsd/internal/model"
	"metricsd/internal/texts"
)

// Manager - обёртка над VBoxManage для high-профиля.
type Manager struct {
	ImagesDir string
	Debug     bool
}

func New_Manager(dataDir string, debug bool) *Manager {
	dir := filepath.Join(dataDir, "vm-images")
	_ = os.MkdirAll(dir, 0o755)
	return &Manager{ImagesDir: dir, Debug: debug}
}

func (m *Manager) debug(msg string) {
	if m.Debug {
		println("[DEBUG] vbox:", msg)
	}
}

func (m *Manager) run(args ...string) (string, error) {
	cmd := exec.Command("VBoxManage", args...)
	m.debug(strings.Join(cmd.Args, " "))
	out, err := cmd.CombinedOutput()
	text := strings.TrimSpace(string(out))
	if err != nil {
		if text == "" {
			text = err.Error()
		}
		return text, fmt.Errorf("%s", text)
	}
	return text, nil
}

func (m *Manager) Ensure_VBoxManage() error {
	if _, err := exec.LookPath("VBoxManage"); err != nil {
		return fmt.Errorf(texts.MsgVmVBoxMissing)
	}
	_, err := m.run("--version")
	return err
}

func (m *Manager) imagePath(token string) string {
	return filepath.Join(m.ImagesDir, token+".ova")
}

func (m *Manager) vmExists(name string) bool {
	out, err := m.run("list", "vms")
	if err != nil {
		return false
	}
	needle := `"` + name + `"`
	for _, line := range strings.Split(out, "\n") {
		if strings.Contains(line, needle) {
			return true
		}
	}
	return false
}

func (m *Manager) snapshotExists(vmName, snap string) bool {
	out, err := m.run("snapshot", vmName, "list", "--machinereadable")
	if err != nil {
		return false
	}
	return strings.Contains(out, `SnapshotName="`+snap+`"`) ||
		strings.Contains(out, `CurrentSnapshotName="`+snap+`"`)
}

func (m *Manager) applyResources(emu model.EmulationBlock) error {
	name := strings.TrimSpace(emu.VmName)
	cpus := emu.Cpus
	if cpus < 1 {
		cpus = 2
	}
	mem := emu.MemoryMb
	if mem < 512 {
		mem = 4096
	}
	if _, err := m.run("modifyvm", name, "--cpus", strconv.Itoa(cpus)); err != nil {
		return err
	}
	_, err := m.run("modifyvm", name, "--memory", strconv.Itoa(mem))
	return err
}

func (m *Manager) clearNatRules(vmName string) {
	// Удаляем старые pf1..pf16 если есть - ошибки игнорим.
	for i := 1; i <= 16; i++ {
		_, _ = m.run("modifyvm", vmName, "--natpf1", "delete", fmt.Sprintf("hf%d", i))
	}
}

func (m *Manager) applyExpose(emu model.EmulationBlock) error {
	name := strings.TrimSpace(emu.VmName)
	m.clearNatRules(name)
	for i, rule := range emu.Expose {
		proto := strings.ToLower(strings.TrimSpace(rule.Proto))
		if proto == "" {
			proto = "tcp"
		}
		spec := fmt.Sprintf(
			"hf%d,%s,,%d,,%d",
			i+1,
			proto,
			rule.HostPort,
			rule.GuestPort,
		)
		if _, err := m.run("modifyvm", name, "--natpf1", spec); err != nil {
			return err
		}
	}
	return nil
}

func (m *Manager) ensureSnapshot(emu model.EmulationBlock) error {
	name := strings.TrimSpace(emu.VmName)
	snap := strings.TrimSpace(emu.Snapshot)
	if snap == "" {
		snap = "clean"
	}
	if m.snapshotExists(name, snap) {
		return nil
	}
	_, err := m.run("snapshot", name, "take", snap, "--description", "honeyforge clean")
	return err
}

// Ensure - скачанный OVA уже на диске; import / ресурсы / NAT / snapshot.
func (m *Manager) Ensure(emu model.EmulationBlock) (string, error) {
	if err := m.Ensure_VBoxManage(); err != nil {
		return "", err
	}
	name := strings.TrimSpace(emu.VmName)
	if name == "" {
		return "", fmt.Errorf(texts.MsgVmNameEmpty)
	}
	token := strings.TrimSpace(emu.ImageToken)
	if token == "" {
		return "", fmt.Errorf(texts.MsgVmImageTokenEmpty)
	}
	ova := m.imagePath(token)
	if !m.vmExists(name) {
		if _, err := os.Stat(ova); err != nil {
			return "", fmt.Errorf(texts.MsgVmImageMissing, ova)
		}
		if _, err := m.run("import", ova, "--vsys", "0", "--vmname", name); err != nil {
			return "", err
		}
	}
	if err := m.applyResources(emu); err != nil {
		return "", err
	}
	if err := m.applyExpose(emu); err != nil {
		return "", err
	}
	if err := m.ensureSnapshot(emu); err != nil {
		return "", err
	}
	return fmt.Sprintf("ok name=%s image=%s", name, token), nil
}

func (m *Manager) Start(emu model.EmulationBlock) (string, error) {
	if err := m.Ensure_VBoxManage(); err != nil {
		return "", err
	}
	name := strings.TrimSpace(emu.VmName)
	state, _ := m.State(name)
	if state == "running" {
		return "already running", nil
	}
	_, err := m.run("startvm", name, "--type", "headless")
	if err != nil {
		return "", err
	}
	return "started", nil
}

func (m *Manager) Stop(emu model.EmulationBlock) (string, error) {
	if err := m.Ensure_VBoxManage(); err != nil {
		return "", err
	}
	name := strings.TrimSpace(emu.VmName)
	state, _ := m.State(name)
	if state != "running" {
		return "not running", nil
	}
	_, err := m.run("controlvm", name, "poweroff")
	if err != nil {
		return "", err
	}
	return "stopped", nil
}

func (m *Manager) Revert(emu model.EmulationBlock) (string, error) {
	if err := m.Ensure_VBoxManage(); err != nil {
		return "", err
	}
	name := strings.TrimSpace(emu.VmName)
	snap := strings.TrimSpace(emu.Snapshot)
	if snap == "" {
		snap = "clean"
	}
	state, _ := m.State(name)
	if state == "running" {
		_, _ = m.run("controlvm", name, "poweroff")
	}
	if _, err := m.run("snapshot", name, "restore", snap); err != nil {
		return "", err
	}
	return "reverted to " + snap, nil
}

func (m *Manager) State(vmName string) (string, error) {
	out, err := m.run("showvminfo", vmName, "--machinereadable")
	if err != nil {
		return "", err
	}
	for _, line := range strings.Split(out, "\n") {
		if strings.HasPrefix(line, "VMState=") {
			return strings.Trim(strings.TrimPrefix(line, "VMState="), `"`), nil
		}
	}
	return "unknown", nil
}

func (m *Manager) Status(emu model.EmulationBlock) (string, error) {
	if err := m.Ensure_VBoxManage(); err != nil {
		return "", err
	}
	name := strings.TrimSpace(emu.VmName)
	state, err := m.State(name)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("name=%s state=%s", name, state), nil
}

// ImageLocalPath - куда агент кладёт скачанный OVA.
func (m *Manager) ImageLocalPath(token string) string {
	return m.imagePath(token)
}
