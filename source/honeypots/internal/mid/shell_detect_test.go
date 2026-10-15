package mid

import (
	"strings"
	"testing"
	"time"
)

func Test_FakeShell_PassesCommonProbes(t *testing.T) {
	s := New_FakeShell("ubuntu", "web-lab-01", "builtin", nil, nil, 22, nil, nil)

	out, _ := s.Run_Line("echo $BASH_VERSION")
	if !strings.Contains(out, "5.1.16") {
		t.Fatalf("BASH_VERSION: %q", out)
	}
	out, _ = s.Run_Line("echo $SHELL")
	if strings.TrimSpace(out) != "/bin/bash" {
		t.Fatalf("SHELL: %q", out)
	}
	out, _ = s.Run_Line("echo $0")
	if strings.TrimSpace(out) != "-bash" {
		t.Fatalf("$0: %q", out)
	}
	out, _ = s.Run_Line("file /bin/bash")
	if !strings.Contains(out, "ELF 64-bit") {
		t.Fatalf("file bash: %q", out)
	}
	out, _ = s.Run_Line("ls -la /bin/bash")
	if !strings.Contains(out, "bash") {
		t.Fatalf("ls bash: %q", out)
	}
	out, _ = s.Run_Line("which ls")
	if strings.TrimSpace(out) != "/bin/ls" {
		t.Fatalf("which ls: %q", out)
	}
	out, _ = s.Run_Line("cat /etc/passwd | grep root | wc -l")
	if strings.TrimSpace(out) == "" || strings.Contains(out, "not found") {
		t.Fatalf("pipe wc: %q", out)
	}
	out, _ = s.Run_Line("echo test > /tmp/testfile && cat /tmp/testfile")
	if !strings.Contains(out, "test") {
		t.Fatalf("write/read: %q", out)
	}
	out, _ = s.Run_Line("cat /proc/cpuinfo | head -n 1")
	if !strings.Contains(out, "processor") {
		t.Fatalf("cpuinfo: %q", out)
	}
	out, _ = s.Run_Line("cat /proc/self/exe | head -c 4")
	if !strings.HasPrefix(out, "\x7fELF") {
		t.Fatalf("self/exe: %q", out)
	}
	out, _ = s.Run_Line("ps aux")
	if !strings.Contains(out, "bash") || !strings.Contains(out, "USER") {
		t.Fatalf("ps aux: %q", out)
	}
	out, _ = s.Run_Line("netstat -tuln")
	if !strings.Contains(out, "LISTEN") {
		t.Fatalf("netstat: %q", out)
	}
}

func Test_FakeShell_Wave2AntiDetect(t *testing.T) {
	ip := "203.0.113.9"
	port := 44321
	s := New_FakeShell("ubuntu", "web-lab-01", "builtin", &ip, &port, 22, nil, nil)

	out, _ := s.Run_Line("echo $(id -u)")
	if strings.TrimSpace(out) != "1000" {
		t.Fatalf("$(id -u): %q", out)
	}
	out, _ = s.Run_Line("test -f /bin/bash && echo ok")
	if !strings.Contains(out, "ok") {
		t.Fatalf("test -f: %q", out)
	}
	out, _ = s.Run_Line("echo $((2+2))")
	if strings.TrimSpace(out) != "4" {
		t.Fatalf("arith: %q", out)
	}

	a := New_FakeShell("ubuntu", "host-aaa", "builtin", nil, nil, 22, nil, nil)
	b := New_FakeShell("ubuntu", "host-bbb", "builtin", nil, nil, 22, nil, nil)
	ha, _ := a.Run_Line("md5sum /bin/bash")
	hb, _ := b.Run_Line("md5sum /bin/bash")
	if strings.Fields(ha)[0] == strings.Fields(hb)[0] {
		t.Fatalf("md5sum fingerprint same: %q vs %q", ha, hb)
	}

	started := time.Now()
	_, _ = s.Run_Line("sleep 1")
	if time.Since(started) < 900*time.Millisecond {
		t.Fatalf("sleep too fast: %v", time.Since(started))
	}

	out, _ = s.Run_Line("echo x > /etc/hostname")
	if !strings.Contains(out, "Permission denied") {
		t.Fatalf("etc write: %q", out)
	}
	out, _ = s.Run_Line("readlink /proc/self/exe")
	if strings.TrimSpace(out) != "/bin/bash" {
		t.Fatalf("readlink: %q", out)
	}
	out, _ = s.Run_Line("ls /proc")
	if !strings.Contains(out, "812") || !strings.Contains(out, "990") || !strings.Contains(out, "self") {
		t.Fatalf("ls /proc: %q", out)
	}
	out, _ = s.Run_Line("echo $SSH_CLIENT")
	if !strings.Contains(out, ip) {
		t.Fatalf("SSH_CLIENT: %q", out)
	}
	out, _ = s.Run_Line("command -v ls")
	if strings.TrimSpace(out) != "/bin/ls" {
		t.Fatalf("command -v: %q", out)
	}
	out, _ = s.Run_Line("tty")
	if strings.TrimSpace(out) != "/dev/pts/0" {
		t.Fatalf("tty: %q", out)
	}
	out, _ = s.Run_Line("ip route")
	if !strings.Contains(out, "default via") {
		t.Fatalf("ip route: %q", out)
	}
	out, _ = s.Run_Line("stat /bin/bash")
	if !strings.Contains(out, "Inode:") || !strings.Contains(out, "File:") {
		t.Fatalf("stat: %q", out)
	}
}

func Test_FakeShell_Wave3AntiDetect(t *testing.T) {
	ip := "198.51.100.44"
	port := 51234
	s := New_FakeShell("ubuntu", "web-lab-01", "builtin", &ip, &port, 22, nil, nil)

	uname, _ := s.Run_Line("uname -a")
	if !strings.Contains(uname, "5.15.0-91-generic") {
		t.Fatalf("uname: %q", uname)
	}
	osrel, _ := s.Run_Line("cat /etc/os-release")
	if !strings.Contains(osrel, `VERSION_ID="22.04"`) || !strings.Contains(osrel, "VERSION_CODENAME=jammy") {
		t.Fatalf("os-release: %q", osrel)
	}
	if !strings.Contains(osrel, "Ubuntu 22.04") {
		t.Fatalf("os-release distro: %q", osrel)
	}

	ldd, _ := s.Run_Line("ldd /bin/bash")
	if !strings.Contains(ldd, "libc.so.6") || !strings.Contains(ldd, "ld-linux") {
		t.Fatalf("ldd bash: %q", ldd)
	}
	lddTxt, _ := s.Run_Line("ldd /etc/hostname")
	if !strings.Contains(lddTxt, "not a dynamic executable") {
		t.Fatalf("ldd text: %q", lddTxt)
	}

	wget, _ := s.Run_Line("wget http://example.com/")
	if !strings.Contains(wget, "wget:") || strings.Contains(wget, "curl:") {
		t.Fatalf("wget: %q", wget)
	}
	curl, _ := s.Run_Line("curl http://example.com/")
	if !strings.Contains(curl, "curl: (6)") {
		t.Fatalf("curl: %q", curl)
	}

	sshClient, _ := s.Run_Line("echo $SSH_CLIENT")
	if !strings.Contains(sshClient, ip) {
		t.Fatalf("SSH_CLIENT: %q", sshClient)
	}
}
