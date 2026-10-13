package mid

import (
	"strings"
	"testing"
)

func Test_FakeShell_FsMutationsStayInSession(t *testing.T) {
	a := New_FakeShell("alice", "host-a", "builtin", nil, nil, 22, nil, nil)
	out, _ := a.Run_Line("mkdir -p ~/work/logs")
	if out != "" {
		t.Fatalf("mkdir: %q", out)
	}
	out, _ = a.Run_Line("echo hello > ~/work/logs/note.txt")
	if out != "" {
		t.Fatalf("redirect: %q", out)
	}
	out, _ = a.Run_Line("cat ~/work/logs/note.txt")
	if strings.TrimSpace(out) != "hello" {
		t.Fatalf("cat got %q", out)
	}

	// Новая сессия - чистый builtin, без следов прошлой
	b := New_FakeShell("alice", "host-a", "builtin", nil, nil, 22, nil, nil)
	out, _ = b.Run_Line("ls ~/work")
	if !strings.Contains(out, "No such file") {
		t.Fatalf("вторая сессия должна быть чистой, got %q", out)
	}
}

func Test_FakeShell_RmCpMvFind(t *testing.T) {
	s := New_FakeShell("root", "box", "ubuntu-22.04", nil, nil, 22, nil, nil)
	_, _ = s.Run_Line("mkdir /tmp/d")
	_, _ = s.Run_Line("echo x > /tmp/d/a.txt")
	_, _ = s.Run_Line("cp /tmp/d/a.txt /tmp/d/b.txt")
	_, _ = s.Run_Line("mv /tmp/d/b.txt /tmp/d/c.txt")
	out, _ := s.Run_Line("find /tmp/d -name '*.txt'")
	if !strings.Contains(out, "/tmp/d/a.txt") || !strings.Contains(out, "/tmp/d/c.txt") {
		t.Fatalf("find: %q", out)
	}
	_, _ = s.Run_Line("rm -rf /tmp/d")
	out, _ = s.Run_Line("ls /tmp/d")
	if !strings.Contains(out, "No such file") {
		t.Fatalf("rm -rf: %q", out)
	}
}
