package mid

import (
	"fmt"
	"strings"

	"honeyforge/honeypots/internal/model"
	"honeyforge/honeypots/internal/state"
	"honeyforge/honeypots/internal/texts"
)

type EventHandler func(model.AgentEvent)

type FakeShell struct {
	Username   string
	Hostname   string
	SourceIP   *string
	SourcePort *int
	Port       int
	OnEvent    EventHandler
	Cwd        string
	Suffix     string
	Tree       map[string]string
}

func New_FakeShell(
	username, hostname, fsPack string,
	sourceIP *string,
	sourcePort *int,
	port int,
	onEvent EventHandler,
) *FakeShell {
	if username == "" {
		username = "user"
	}
	cwd := "/home/" + username
	suffix := "$"
	if username == "root" {
		cwd = "/root"
		suffix = "#"
	}
	tree := build_Tree(username, hostname)
	pack := strings.TrimSpace(fsPack)
	if pack != "" && pack != "ubuntu-22.04" {
		tree["/etc/issue"] = pack + "\n"
	}
	return &FakeShell{
		Username:   username,
		Hostname:   hostname,
		SourceIP:   sourceIP,
		SourcePort: sourcePort,
		Port:       port,
		OnEvent:    onEvent,
		Cwd:        cwd,
		Suffix:     suffix,
		Tree:       tree,
	}
}

func build_Tree(username, hostname string) map[string]string {
	home := "/home/" + username
	if username == "root" {
		home = "/root"
	}
	return map[string]string{
		"/etc/hostname":      hostname + "\n",
		"/etc/issue":         texts.MsgShellIssue,
		home + "/readme.txt": texts.MsgShellReadme,
	}
}

func (s *FakeShell) Prompt() string {
	return fmt.Sprintf(texts.MsgShellPrompt, s.Username, s.Hostname, s.Cwd, s.Suffix)
}

func (s *FakeShell) emit_Command(command string) {
	if s.OnEvent == nil {
		return
	}
	cmd := command
	if len(cmd) > 200 {
		cmd = cmd[:200]
	}
	s.OnEvent(model.AgentEvent{
		EventType:  "shell_command",
		SourceIP:   s.SourceIP,
		SourcePort: s.SourcePort,
		OccurredAt: state.Now_Iso(),
		Payload: map[string]any{
			"port":     s.Port,
			"username": s.Username,
			"cwd":      s.Cwd,
			"command":  cmd,
		},
	})
}

func (s *FakeShell) Run_Line(line string) (string, bool) {
	stripped := strings.TrimSpace(line)
	if stripped == "" {
		return "", false
	}
	s.emit_Command(stripped)
	parts := strings.Fields(stripped)
	cmd := parts[0]
	args := make([]string, 0, len(parts)-1)
	for _, item := range parts[1:] {
		if !strings.HasPrefix(item, "-") {
			args = append(args, item)
		}
	}
	switch cmd {
	case "exit", "logout", "quit":
		return texts.MsgShellLogout, true
	case "help":
		return texts.MsgShellHelp, false
	case "whoami":
		return s.Username + "\n", false
	case "hostname":
		return s.Hostname + "\n", false
	case "pwd":
		return s.Cwd + "\n", false
	case "id":
		return fmt.Sprintf(texts.MsgShellID, s.Username, s.Username, s.Username), false
	case "uname":
		return fmt.Sprintf(texts.MsgShellUname, s.Hostname), false
	case "echo":
		return strings.Join(parts[1:], " ") + "\n", false
	case "ls":
		return s.cmd_Ls(args), false
	case "cd":
		return s.cmd_Cd(args), false
	case "cat":
		return s.cmd_Cat(args), false
	default:
		return fmt.Sprintf(texts.MsgShellNotFound, cmd), false
	}
}

func normalize_Path(cwd, raw string) string {
	var path string
	if strings.HasPrefix(raw, "/") {
		path = raw
	} else {
		base := cwd
		if cwd == "/" {
			base = ""
		}
		path = base + "/" + raw
	}
	parts := []string{}
	for _, part := range strings.Split(path, "/") {
		if part == "" || part == "." {
			continue
		}
		if part == ".." {
			if len(parts) > 0 {
				parts = parts[:len(parts)-1]
			}
			continue
		}
		parts = append(parts, part)
	}
	if len(parts) == 0 {
		return "/"
	}
	return "/" + strings.Join(parts, "/")
}

func list_Names(tree map[string]string, path string) []string {
	prefix := path
	if path == "/" {
		prefix = ""
	}
	seen := map[string]bool{}
	names := []string{}
	for full := range tree {
		var rest string
		if path == "/" {
			rest = full[1:]
		} else if full == path {
			continue
		} else if strings.HasPrefix(full, prefix+"/") {
			rest = full[len(prefix)+1:]
		} else {
			continue
		}
		name := strings.SplitN(rest, "/", 2)[0]
		if name != "" && !seen[name] {
			seen[name] = true
			names = append(names, name)
		}
	}
	for i := 0; i < len(names); i++ {
		for j := i + 1; j < len(names); j++ {
			if names[j] < names[i] {
				names[i], names[j] = names[j], names[i]
			}
		}
	}
	return names
}

func is_Dir(tree map[string]string, path string) bool {
	if path == "/" {
		return true
	}
	prefix := path + "/"
	for full := range tree {
		if strings.HasPrefix(full, prefix) {
			return true
		}
	}
	return false
}

func (s *FakeShell) cmd_Ls(args []string) string {
	path := s.Cwd
	if len(args) > 0 {
		path = normalize_Path(s.Cwd, args[0])
	}
	if _, ok := s.Tree[path]; ok && !is_Dir(s.Tree, path) {
		parts := strings.Split(path, "/")
		return parts[len(parts)-1] + "\n"
	}
	if path != "/" && s.Tree[path] == "" && !is_Dir(s.Tree, path) {
		msg := fmt.Sprintf(texts.MsgShellNoFile, path)
		return strings.Replace(msg, "cat:", "ls:", 1)
	}
	names := list_Names(s.Tree, path)
	if len(names) == 0 {
		return ""
	}
	return strings.Join(names, "  ") + "\n"
}

func (s *FakeShell) cmd_Cd(args []string) string {
	raw := "/home/" + s.Username
	if s.Username == "root" {
		raw = "/root"
	}
	if len(args) > 0 {
		raw = args[0]
	}
	path := normalize_Path(s.Cwd, raw)
	if _, ok := s.Tree[path]; ok && !is_Dir(s.Tree, path) {
		return fmt.Sprintf(texts.MsgShellNotDir, path)
	}
	allowedEmpty := path == "/root" || path == "/home" || path == "/home/"+s.Username || path == "/etc"
	if path != "/" && !is_Dir(s.Tree, path) && !allowedEmpty {
		msg := fmt.Sprintf(texts.MsgShellNoFile, path)
		return strings.Replace(msg, "cat:", "cd:", 1)
	}
	s.Cwd = path
	return ""
}

func (s *FakeShell) cmd_Cat(args []string) string {
	if len(args) == 0 {
		return texts.MsgShellCatUsage
	}
	path := normalize_Path(s.Cwd, args[0])
	body, ok := s.Tree[path]
	if !ok {
		return fmt.Sprintf(texts.MsgShellNoFile, path)
	}
	return body
}
