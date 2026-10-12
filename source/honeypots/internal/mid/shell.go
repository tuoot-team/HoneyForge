package mid

import (
	"fmt"
	"hash/fnv"
	"strings"
	"time"

	"honeyforge/honeypots/internal/model"
	"honeyforge/honeypots/internal/state"
	"honeyforge/honeypots/internal/texts"
)

type EventHandler func(model.AgentEvent)

type chainPart struct {
	cmd    string
	needOK bool
}

type FakeShell struct {
	Username   string
	Hostname   string
	SourceIP   *string
	SourcePort *int
	Port       int
	OnEvent    EventHandler
	Cwd        string
	Suffix     string
	Home       string
	Addr       string
	UptimeDays int
	Tree       map[string]string
	Dirs       map[string]struct{}
	History    []string
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
	home := "/home/" + username
	suffix := "$"
	if username == "root" {
		home = "/root"
		suffix = "#"
	}
	addr, days := fake_HostFacts(hostname)
	tree := build_Tree(username, hostname, home, addr)
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
		Cwd:        home,
		Suffix:     suffix,
		Home:       home,
		Addr:       addr,
		UptimeDays: days,
		Tree:       tree,
		Dirs:       fill_Dirs(tree),
	}
}

func fake_HostFacts(hostname string) (string, int) {
	h := fnv.New32a()
	_, _ = h.Write([]byte(hostname))
	n := h.Sum32()
	last := n & 0xff
	if last == 0 || last == 255 {
		last = 10
	}
	addr := fmt.Sprintf("10.%d.%d.%d", (n>>16)&0xff, (n>>8)&0xff, last)
	return addr, int(n%40) + 3
}

func build_Tree(username, hostname, home, addr string) map[string]string {
	return map[string]string{
		"/etc/hostname":         hostname + "\n",
		"/etc/issue":            texts.MsgShellIssue,
		"/etc/os-release":       texts.MsgShellOsRelease,
		"/etc/passwd":           texts.MsgShellPasswd + user_PasswdLine(username),
		"/etc/group":            fmt.Sprintf(texts.MsgShellGroup, username),
		"/etc/hosts":            fmt.Sprintf("127.0.0.1 localhost\n%s %s\n", addr, hostname),
		"/etc/resolv.conf":      texts.MsgShellResolv,
		"/proc/version":         fmt.Sprintf(texts.MsgShellUname, hostname),
		"/var/log/syslog":       fmt.Sprintf(texts.MsgShellSyslog, hostname, hostname, username),
		home + "/readme.txt":    texts.MsgShellReadme,
		home + "/.bashrc":       texts.MsgShellBashrc,
		home + "/.bash_history": texts.MsgShellHistory,
	}
}

func fill_Dirs(tree map[string]string) map[string]struct{} {
	dirs := map[string]struct{}{"/": {}}
	for full := range tree {
		dir := full
		for {
			slash := strings.LastIndex(dir, "/")
			if slash <= 0 {
				break
			}
			dir = dir[:slash]
			dirs[dir] = struct{}{}
		}
	}
	for _, extra := range []string{"/bin", "/dev", "/home", "/opt", "/proc", "/sbin", "/tmp", "/usr", "/var"} {
		dirs[extra] = struct{}{}
	}
	return dirs
}

func user_PasswdLine(username string) string {
	if username == "root" {
		return ""
	}
	return fmt.Sprintf("%s:x:1000:1000:%s:/home/%s:/bin/bash\n", username, username, username)
}

func (s *FakeShell) Prompt() string {
	return fmt.Sprintf(texts.MsgShellPrompt, s.Username, s.Hostname, s.Cwd, s.Suffix)
}

func (s *FakeShell) emit_Command(command string) {
	s.History = append(s.History, command)
	if len(s.History) > 40 {
		s.History = s.History[len(s.History)-40:]
	}
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
	var out strings.Builder
	ok := true
	for _, part := range split_Chain(stripped) {
		if part.needOK && !ok {
			break
		}
		piece, stop := s.run_Pipes(part.cmd)
		out.WriteString(piece)
		ok = !command_Failed(piece)
		if stop {
			return out.String(), true
		}
	}
	return out.String(), false
}

// ; идёт дальше всегда, && только если предыдущая команда не упала.
func split_Chain(line string) []chainPart {
	var parts []chainPart
	var buf strings.Builder
	needOK := false
	flush := func() {
		cmd := strings.TrimSpace(buf.String())
		buf.Reset()
		if cmd != "" {
			parts = append(parts, chainPart{cmd: cmd, needOK: needOK})
		}
		needOK = false
	}
	for i := 0; i < len(line); i++ {
		if line[i] == ';' {
			flush()
			continue
		}
		if line[i] == '&' && i+1 < len(line) && line[i+1] == '&' {
			flush()
			needOK = true
			i++
			continue
		}
		buf.WriteByte(line[i])
	}
	flush()
	return parts
}

func command_Failed(out string) bool {
	needles := []string{
		"not found",
		"No such file",
		"Not a directory",
		"not in the sudoers",
		"Could not resolve",
		"missing file operand",
	}
	for _, needle := range needles {
		if strings.Contains(out, needle) {
			return true
		}
	}
	return false
}

func (s *FakeShell) run_Pipes(line string) (string, bool) {
	stages := strings.Split(line, "|")
	out, stop := s.run_One(strings.TrimSpace(stages[0]))
	if stop || len(stages) == 1 {
		return out, stop
	}
	for _, stage := range stages[1:] {
		out = apply_Pipe(out, strings.TrimSpace(stage))
	}
	return out, false
}

func apply_Pipe(input, stage string) string {
	parts := strings.Fields(stage)
	if len(parts) == 0 {
		return input
	}
	switch parts[0] {
	case "grep":
		needle := ""
		if args := positional(parts); len(args) > 0 {
			needle = args[0]
		}
		if input == "" {
			return ""
		}
		var b strings.Builder
		for _, row := range strings.Split(strings.TrimRight(input, "\n"), "\n") {
			if needle == "" || strings.Contains(row, needle) {
				b.WriteString(row)
				b.WriteByte('\n')
			}
		}
		return b.String()
	case "head", "tail":
		n := pipe_Count(parts, 10)
		rows := strings.Split(strings.TrimRight(input, "\n"), "\n")
		if input == "" {
			return ""
		}
		if parts[0] == "head" {
			if n > len(rows) {
				n = len(rows)
			}
			return strings.Join(rows[:n], "\n") + "\n"
		}
		if n > len(rows) {
			n = len(rows)
		}
		return strings.Join(rows[len(rows)-n:], "\n") + "\n"
	case "wc":
		rows := strings.Split(strings.TrimRight(input, "\n"), "\n")
		if input == "" {
			rows = nil
		}
		return fmt.Sprintf("%d\n", len(rows))
	default:
		return fmt.Sprintf(texts.MsgShellNotFound, parts[0])
	}
}

func pipe_Count(parts []string, fallback int) int {
	pending := false
	for _, part := range parts[1:] {
		if part == "-n" || part == "--lines" {
			pending = true
			continue
		}
		raw := part
		if strings.HasPrefix(part, "-") {
			raw = strings.TrimLeft(part, "-")
		} else if !pending && strings.Contains(part, "/") {
			continue
		}
		n := 0
		ok := raw != ""
		for _, ch := range raw {
			if ch < '0' || ch > '9' {
				ok = false
				break
			}
			n = n*10 + int(ch-'0')
		}
		if ok && n > 0 {
			return n
		}
		pending = false
	}
	return fallback
}

func (s *FakeShell) run_One(line string) (string, bool) {
	parts := strings.Fields(line)
	if len(parts) == 0 {
		return "", false
	}
	cmd := parts[0]
	args := positional(parts)
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
		if has_Flag(parts, "u") {
			if s.Username == "root" {
				return "0\n", false
			}
			return "1000\n", false
		}
		if s.Username == "root" {
			return texts.MsgShellIDRoot, false
		}
		return fmt.Sprintf(texts.MsgShellIDUser, s.Username, s.Username, s.Username), false
	case "uname":
		if has_Flag(parts, "a") {
			return fmt.Sprintf(texts.MsgShellUname, s.Hostname), false
		}
		return "Linux\n", false
	case "echo":
		return strings.Join(parts[1:], " ") + "\n", false
	case "ls":
		return s.cmd_Ls(parts), false
	case "cd":
		return s.cmd_Cd(args), false
	case "cat", "head", "tail":
		return s.cmd_Cat(args), false
	case "history":
		return s.cmd_History(), false
	case "env":
		return s.cmd_Env(), false
	case "ps":
		return texts.MsgShellPs, false
	case "uptime":
		return fmt.Sprintf(texts.MsgShellUptime, time.Now().Format("15:04:05"), s.UptimeDays), false
	case "df":
		return texts.MsgShellDf, false
	case "free":
		return texts.MsgShellFree, false
	case "ip", "ifconfig":
		brd := s.Addr
		if dot := strings.LastIndex(s.Addr, "."); dot > 0 {
			brd = s.Addr[:dot] + ".255"
		}
		return fmt.Sprintf(texts.MsgShellIp, s.Addr, brd), false
	case "w", "who":
		return fmt.Sprintf("%s   pts/0    %s\n", s.Username, s.Addr), false
	case "sudo":
		if s.Username != "root" {
			return fmt.Sprintf(texts.MsgShellSudo, s.Username), false
		}
		rest := strings.TrimSpace(strings.TrimPrefix(line, "sudo"))
		if rest == "" {
			return "", false
		}
		return s.run_One(rest)
	case "wget", "curl", "nc", "netcat":
		host := net_Host(args)
		if host == "" {
			return texts.MsgShellNoNetBare, false
		}
		return fmt.Sprintf(texts.MsgShellNoNet, host), false
	case "which":
		if len(args) == 0 || !known_Command(args[0]) {
			return "", false
		}
		return "/usr/bin/" + args[0] + "\n", false
	case "clear":
		return "\033[H\033[2J", false
	default:
		return fmt.Sprintf(texts.MsgShellNotFound, cmd), false
	}
}

func known_Command(name string) bool {
	switch name {
	case "ls", "pwd", "cd", "cat", "whoami", "id", "hostname", "uname",
		"ps", "env", "history", "uptime", "df", "free", "ip", "echo",
		"which", "wget", "curl", "sudo", "clear", "grep", "head", "tail", "wc":
		return true
	default:
		return false
	}
}

func net_Host(args []string) string {
	if len(args) == 0 {
		return ""
	}
	raw := args[len(args)-1]
	raw = strings.TrimPrefix(raw, "https://")
	raw = strings.TrimPrefix(raw, "http://")
	raw = strings.SplitN(raw, "/", 2)[0]
	raw = strings.SplitN(raw, ":", 2)[0]
	return raw
}

func has_Flag(parts []string, letter string) bool {
	for _, part := range parts[1:] {
		if strings.HasPrefix(part, "-") && strings.Contains(part, letter) {
			return true
		}
	}
	return false
}

func positional(parts []string) []string {
	args := make([]string, 0, len(parts))
	for _, item := range parts[1:] {
		if strings.HasPrefix(item, "-") && item != "-" {
			continue
		}
		args = append(args, item)
	}
	return args
}

func (s *FakeShell) cmd_History() string {
	var b strings.Builder
	prior := strings.Split(strings.TrimRight(texts.MsgShellHistory, "\n"), "\n")
	n := 1
	for _, row := range prior {
		if row == "" {
			continue
		}
		fmt.Fprintf(&b, "  %d  %s\n", n, row)
		n++
	}
	for _, row := range s.History {
		fmt.Fprintf(&b, "  %d  %s\n", n, row)
		n++
	}
	return b.String()
}

func (s *FakeShell) cmd_Env() string {
	return fmt.Sprintf(
		"USER=%s\nHOME=%s\nPWD=%s\nSHELL=/bin/bash\nHOSTNAME=%s\n",
		s.Username, s.Home, s.Cwd, s.Hostname,
	)
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

func (s *FakeShell) list_Names(path string, withDot bool) []string {
	prefix := path
	if path == "/" {
		prefix = ""
	}
	seen := map[string]bool{}
	names := []string{}
	add := func(name string) {
		if name == "" || seen[name] {
			return
		}
		if !withDot && strings.HasPrefix(name, ".") {
			return
		}
		seen[name] = true
		names = append(names, name)
	}
	for full := range s.Tree {
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
		add(strings.SplitN(rest, "/", 2)[0])
	}
	for dir := range s.Dirs {
		if dir == "/" || dir == path {
			continue
		}
		slash := strings.LastIndex(dir, "/")
		parent := "/"
		if slash > 0 {
			parent = dir[:slash]
		}
		if parent == path {
			add(dir[slash+1:])
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

func (s *FakeShell) is_Dir(path string) bool {
	if path == "/" {
		return true
	}
	_, ok := s.Dirs[path]
	return ok
}

func (s *FakeShell) cmd_Ls(parts []string) string {
	args := positional(parts)
	path := s.Cwd
	if len(args) > 0 {
		path = normalize_Path(s.Cwd, args[0])
	}
	long := has_Flag(parts, "l")
	withDot := has_Flag(parts, "a")
	if _, ok := s.Tree[path]; ok && !s.is_Dir(path) {
		name := path[strings.LastIndex(path, "/")+1:]
		if long {
			return s.format_Entry(path, name) + "\n"
		}
		return name + "\n"
	}
	if !s.is_Dir(path) {
		msg := fmt.Sprintf(texts.MsgShellNoFile, path)
		return strings.Replace(msg, "cat:", "ls:", 1)
	}
	names := s.list_Names(path, withDot)
	if long {
		var b strings.Builder
		fmt.Fprintf(&b, "total %d\n", len(names))
		if withDot {
			b.WriteString(s.format_Entry(path, ".") + "\n")
			b.WriteString(s.format_Entry(path, "..") + "\n")
		}
		for _, name := range names {
			full := path
			if path == "/" {
				full = "/" + name
			} else {
				full = path + "/" + name
			}
			b.WriteString(s.format_Entry(full, name) + "\n")
		}
		return b.String()
	}
	if len(names) == 0 {
		return ""
	}
	return strings.Join(names, "  ") + "\n"
}

func (s *FakeShell) format_Entry(path, name string) string {
	mode := "-rw-r--r--"
	size := 0
	if name == "." || name == ".." || s.is_Dir(path) {
		mode = "drwxr-xr-x"
		size = 4096
	} else if body, ok := s.Tree[path]; ok {
		size = len(body)
		if strings.HasPrefix(name, ".") {
			mode = "-rw-------"
		}
	}
	owner := "root"
	if strings.HasPrefix(path, s.Home) {
		owner = s.Username
	}
	return fmt.Sprintf("%s 1 %s %s %8d Oct  1 08:15 %s", mode, owner, owner, size, name)
}

func (s *FakeShell) cmd_Cd(args []string) string {
	raw := s.Home
	if len(args) > 0 {
		raw = args[0]
	}
	path := normalize_Path(s.Cwd, raw)
	if _, ok := s.Tree[path]; ok && !s.is_Dir(path) {
		return fmt.Sprintf(texts.MsgShellNotDir, path)
	}
	if !s.is_Dir(path) {
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
	var b strings.Builder
	for _, arg := range args {
		path := normalize_Path(s.Cwd, arg)
		if s.is_Dir(path) {
			return fmt.Sprintf(texts.MsgShellIsDir, path)
		}
		body, ok := s.Tree[path]
		if !ok {
			return fmt.Sprintf(texts.MsgShellNoFile, path)
		}
		b.WriteString(body)
	}
	return b.String()
}
