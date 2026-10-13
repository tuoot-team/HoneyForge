package mid

import (
	"crypto/md5"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
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

// FakeShell - интерактивная сессия. Tree/Dirs/Binary только в RAM;
// при отключении SSH объект уничтожается, изменения FS не сохраняются.
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
	Binary     map[string]struct{}
	BinaryData map[string][]byte
	Meta       map[string]fileMeta
	Env        map[string]string
	History    []string
}

// LoadFsPackBytes - скачать архив пакета; nil = только builtin.
type LoadFsPackBytes func(token string) ([]byte, error)

func New_FakeShell(
	username, hostname, fsPack string,
	sourceIP *string,
	sourcePort *int,
	port int,
	onEvent EventHandler,
	loadPack LoadFsPackBytes,
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
	dirs := fill_Dirs(tree)
	binary := map[string]struct{}{}

	pack := strings.TrimSpace(fsPack)
	if Is_BuiltinFsPack(pack) {
		// как раньше
	} else if Is_PackToken(pack) && loadPack != nil {
		raw, err := loadPack(pack)
		if err != nil {
			fmt.Printf(texts.MsgFsPackFallback+"\n", pack, err)
		} else {
			expanded, expandErr := Expand_Archive(raw)
			if expandErr != nil || expanded == nil {
				fmt.Printf(texts.MsgFsPackFallback+"\n", pack, expandErr)
			} else {
				tree = expanded.Tree
				dirs = expanded.Dirs
				binary = expanded.Binary
				if len(dirs) == 0 {
					dirs = fill_Dirs(tree)
				}
				dirs[home] = struct{}{}
				add_ParentDirs(dirs, home)
			}
		}
	} else if pack != "" {
		// Свободная метка: только /etc/issue, как раньше
		tree["/etc/issue"] = pack + "\n"
	}

	shell := &FakeShell{
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
		Dirs:       dirs,
		Binary:     binary,
		BinaryData: map[string][]byte{},
		Meta:       map[string]fileMeta{},
		Env:        map[string]string{},
	}
	// Системные бинарники и /proc всегда досеиваем - даже поверх fs_pack
	shell.seed_RuntimeFs()
	shell.sync_EnvDefaults()
	return shell
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
		"/etc/motd":             texts.MsgShellMotd,
		"/etc/os-release":       texts.MsgShellOsRelease,
		"/etc/passwd":           texts.MsgShellPasswd + user_PasswdLine(username),
		"/etc/group":            fmt.Sprintf(texts.MsgShellGroup, username),
		"/etc/hosts":            fmt.Sprintf("127.0.0.1 localhost\n%s %s\n", addr, hostname),
		"/etc/resolv.conf":      texts.MsgShellResolv,
		"/proc/version":         fmt.Sprintf(texts.MsgShellUname, hostname),
		"/var/log/syslog":       fmt.Sprintf(texts.MsgShellSyslog, hostname, hostname, username),
		"/var/log/auth.log":     fmt.Sprintf(texts.MsgShellAuthLog, hostname, username, addr, hostname),
		"/tmp/.keep":            "",
		home + "/readme.txt":    texts.MsgShellReadme,
		home + "/.bashrc":       texts.MsgShellBashrc,
		home + "/.profile":      "# ~/.profile\n",
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
	// $(( )), $(...), `...`, затем $VAR
	stripped = s.expand_CommandLine(stripped)
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
		"missing operand",
		"File exists",
		"Directory not empty",
		"Is a directory",
		"Permission denied",
		"command failed",
	}
	for _, needle := range needles {
		if strings.Contains(out, needle) {
			return true
		}
	}
	return false
}

type redirectSpec struct {
	path   string
	append bool
}

func split_Redirect(line string) (string, *redirectSpec) {
	// Ищем > / >> вне простых кавычек
	inSingle, inDouble := false, false
	for i := 0; i < len(line); i++ {
		ch := line[i]
		if ch == '\'' && !inDouble {
			inSingle = !inSingle
			continue
		}
		if ch == '"' && !inSingle {
			inDouble = !inDouble
			continue
		}
		if inSingle || inDouble {
			continue
		}
		if ch == '>' {
			appendMode := false
			end := i
			if i+1 < len(line) && line[i+1] == '>' {
				appendMode = true
				end = i + 1
			}
			left := strings.TrimSpace(line[:i])
			right := strings.TrimSpace(line[end+1:])
			if right == "" {
				return left, nil
			}
			// Первый токен справа - путь
			fields := strings.Fields(right)
			return left, &redirectSpec{path: fields[0], append: appendMode}
		}
	}
	return line, nil
}

func (s *FakeShell) run_Pipes(line string) (string, bool) {
	cmdLine, redir := split_Redirect(line)
	stages := strings.Split(cmdLine, "|")
	out, stop := s.run_One(strings.TrimSpace(stages[0]), "")
	if stop {
		return out, true
	}
	for _, stage := range stages[1:] {
		out = s.apply_Pipe(out, strings.TrimSpace(stage))
	}
	if redir != nil {
		full := s.resolve_Path(redir.path)
		body := out
		if redir.append {
			if prev, ok := s.Tree[full]; ok {
				body = prev + out
			}
		}
		if errMsg := s.write_TextFile(full, body); errMsg != "" {
			if strings.Contains(errMsg, "Permission denied") {
				return errMsg, false
			}
			return fmt.Sprintf(texts.MsgShellRedirect, redir.path), false
		}
		return "", false
	}
	return out, false
}

func (s *FakeShell) apply_Pipe(input, stage string) string {
	parts := strings.Fields(stage)
	if len(parts) == 0 {
		return input
	}
	args := positional(parts)
	switch parts[0] {
	case "grep":
		needle := ""
		if len(args) > 0 {
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
		if n, ok := pipe_ByteCount(parts, 0); ok {
			if parts[0] == "head" {
				if n > len(input) {
					n = len(input)
				}
				return input[:n]
			}
			if n > len(input) {
				n = len(input)
			}
			return input[len(input)-n:]
		}
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
		words := len(strings.Fields(input))
		chars := len(input)
		if has_Flag(parts, "l") {
			return fmt.Sprintf("%d\n", len(rows))
		}
		if has_Flag(parts, "w") {
			return fmt.Sprintf("%d\n", words)
		}
		if has_Flag(parts, "c") {
			return fmt.Sprintf("%d\n", chars)
		}
		return fmt.Sprintf("%7d %7d %7d\n", len(rows), words, chars)
	case "sort":
		rows := strings.Split(strings.TrimRight(input, "\n"), "\n")
		if input == "" {
			return ""
		}
		for i := 0; i < len(rows); i++ {
			for j := i + 1; j < len(rows); j++ {
				if rows[j] < rows[i] {
					rows[i], rows[j] = rows[j], rows[i]
				}
			}
		}
		return strings.Join(rows, "\n") + "\n"
	case "uniq":
		rows := strings.Split(strings.TrimRight(input, "\n"), "\n")
		if input == "" {
			return ""
		}
		var out []string
		var prev string
		first := true
		for _, row := range rows {
			if first || row != prev {
				out = append(out, row)
				prev = row
				first = false
			}
		}
		return strings.Join(out, "\n") + "\n"
	case "tee":
		return s.cmd_Tee(parts, args, input)
	case "base64":
		if has_Flag(parts, "d") {
			raw, err := base64.StdEncoding.DecodeString(strings.TrimSpace(input))
			if err != nil {
				return "base64: invalid input\n"
			}
			return string(raw)
		}
		return base64.StdEncoding.EncodeToString([]byte(input)) + "\n"
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

func (s *FakeShell) run_One(line string, stdin string) (string, bool) {
	parts := strings.Fields(line)
	if len(parts) == 0 {
		return "", false
	}
	cmd := parts[0]
	args := s.expand_Globs(positional(parts))
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
	case "groups":
		if s.Username == "root" {
			return texts.MsgShellGroupsRoot, false
		}
		return fmt.Sprintf(texts.MsgShellGroupsUser, s.Username), false
	case "uname":
		if has_Flag(parts, "a") {
			return fmt.Sprintf(texts.MsgShellUname, s.Hostname), false
		}
		if has_Flag(parts, "r") {
			return "5.15.0-91-generic\n", false
		}
		if has_Flag(parts, "m") {
			return "x86_64\n", false
		}
		return "Linux\n", false
	case "date":
		return fmt.Sprintf(texts.MsgShellDate, time.Now().Format("Mon Jan 2 15:04:05 MST 2006")), false
	case "echo":
		return expand_Echo(parts[1:]) + "\n", false
	case "printf":
		if len(parts) < 2 {
			return "", false
		}
		return strings.ReplaceAll(expand_Echo(parts[1:]), `\n`, "\n") + "\n", false
	case "ls":
		return s.cmd_Ls(parts), false
	case "cd":
		return s.cmd_Cd(args), false
	case "cat", "less", "more":
		if stdin != "" && len(args) == 0 {
			return stdin, false
		}
		return s.cmd_Cat(args), false
	case "head", "tail":
		if stdin != "" && len(args) == 0 {
			return s.apply_Pipe(stdin, line), false
		}
		return s.cmd_HeadTail(cmd, parts, args), false
	case "touch":
		return s.cmd_Touch(args), false
	case "mkdir":
		return s.cmd_Mkdir(parts, args), false
	case "rmdir":
		return s.cmd_Rmdir(args), false
	case "rm":
		return s.cmd_Rm(parts, args), false
	case "mv":
		return s.cmd_Mv(args), false
	case "cp":
		return s.cmd_Cp(parts, args), false
	case "find":
		return s.cmd_Find(args), false
	case "file":
		return s.cmd_File(args), false
	case "test", "[":
		return s.cmd_Test(args), false
	case "[[":
		// Упрощённо как test без обязательного ]]
		clean := args
		if len(clean) > 0 && clean[len(clean)-1] == "]]" {
			clean = clean[:len(clean)-1]
		}
		return s.cmd_Test(clean), false
	case "chmod", "chown", "chgrp":
		return "", false
	case "tee":
		return s.cmd_Tee(parts, args, stdin), false
	case "history":
		return s.cmd_History(), false
	case "env", "printenv":
		return s.cmd_Env(args), false
	case "export":
		return s.cmd_Export(parts[1:]), false
	case "unset":
		for _, name := range args {
			delete(s.Env, name)
		}
		return "", false
	case "ps", "top":
		return s.cmd_Ps(parts), false
	case "uptime":
		return fmt.Sprintf(texts.MsgShellUptime, time.Now().Format("15:04:05"), s.UptimeDays), false
	case "df":
		return texts.MsgShellDf, false
	case "free":
		return texts.MsgShellFree, false
	case "mount":
		return texts.MsgShellMount, false
	case "netstat", "ss":
		return s.cmd_Netstat(parts), false
	case "ip":
		if len(args) > 0 && (args[0] == "route" || args[0] == "r") {
			return s.cmd_IpRoute(), false
		}
		brd := s.Addr
		if dot := strings.LastIndex(s.Addr, "."); dot > 0 {
			brd = s.Addr[:dot] + ".255"
		}
		return fmt.Sprintf(texts.MsgShellIp, s.Addr, brd), false
	case "ifconfig":
		brd := s.Addr
		if dot := strings.LastIndex(s.Addr, "."); dot > 0 {
			brd = s.Addr[:dot] + ".255"
		}
		return fmt.Sprintf(texts.MsgShellIp, s.Addr, brd), false
	case "readlink":
		return s.cmd_Readlink(parts, args), false
	case "stat":
		return s.cmd_Stat(args), false
	case "tty":
		return texts.MsgShellTty, false
	case "w", "who", "last":
		return fmt.Sprintf("%s   pts/0    %s\n", s.Username, s.Addr), false
	case "base64":
		if len(args) > 0 {
			body, errMsg := s.read_Text(args[0])
			if errMsg != "" {
				return errMsg, false
			}
			if has_Flag(parts, "d") {
				raw, err := base64.StdEncoding.DecodeString(strings.TrimSpace(body))
				if err != nil {
					return "base64: invalid input\n", false
				}
				return string(raw), false
			}
			return base64.StdEncoding.EncodeToString([]byte(body)) + "\n", false
		}
		return s.apply_Pipe(stdin, line), false
	case "md5sum", "sha256sum":
		return s.cmd_Checksum(cmd, args, stdin), false
	case "sudo":
		if s.Username != "root" {
			return fmt.Sprintf(texts.MsgShellSudo, s.Username), false
		}
		rest := strings.TrimSpace(strings.TrimPrefix(line, "sudo"))
		if rest == "" {
			return "", false
		}
		return s.run_One(rest, stdin)
	case "ping":
		return s.cmd_Ping(args), false
	case "wget", "curl", "nc", "netcat", "traceroute", "ssh", "scp":
		host := net_Host(args)
		if host == "" {
			return texts.MsgShellNoNetBare, false
		}
		return fmt.Sprintf(texts.MsgShellNoNet, host), false
	case "which", "type", "command":
		name := ""
		if cmd == "command" && len(args) >= 2 && (args[0] == "-v" || args[0] == "-V") {
			name = args[1]
		} else if cmd == "type" && len(args) >= 2 && args[0] == "-t" {
			name = args[1]
			path := which_Path(name)
			if path == "" {
				return "", false
			}
			return "file\n", false
		} else if len(args) > 0 {
			name = args[0]
		}
		if name == "" {
			return "", false
		}
		path := which_Path(name)
		if path == "" {
			return "", false
		}
		return path + "\n", false
	case "true", ":":
		return "", false
	case "false":
		return "false: command failed\n", false
	case "sleep":
		return s.cmd_Sleep(args), false
	case "clear":
		return "\033[H\033[2J", false
	default:
		return fmt.Sprintf(texts.MsgShellNotFound, cmd), false
	}
}

func expand_Echo(args []string) string {
	var b strings.Builder
	for i, arg := range args {
		if i > 0 {
			b.WriteByte(' ')
		}
		arg = strings.ReplaceAll(arg, `\n`, "\n")
		arg = strings.ReplaceAll(arg, `\t`, "\t")
		b.WriteString(arg)
	}
	return b.String()
}

func (s *FakeShell) read_Text(raw string) (string, string) {
	full := s.resolve_Path(raw)
	return s.read_BytesAsString(full)
}

func (s *FakeShell) cmd_Checksum(cmd string, args []string, stdin string) string {
	hashOne := func(data string, label string) string {
		var sum []byte
		if cmd == "md5sum" {
			h := md5.Sum([]byte(data))
			sum = h[:]
		} else {
			h := sha256.Sum256([]byte(data))
			sum = h[:]
		}
		return hex.EncodeToString(sum) + "  " + label + "\n"
	}
	if len(args) == 0 {
		return hashOne(stdin, "-")
	}
	var b strings.Builder
	for _, arg := range args {
		body, errMsg := s.read_Text(arg)
		if errMsg != "" {
			return errMsg
		}
		b.WriteString(hashOne(body, arg))
	}
	return b.String()
}

func known_Command(name string) bool {
	return which_Path(name) != ""
}

func which_Path(name string) string {
	inBin := map[string]struct{}{
		"ls": {}, "pwd": {}, "cd": {}, "cat": {}, "less": {}, "more": {}, "touch": {},
		"mkdir": {}, "rmdir": {}, "rm": {}, "mv": {}, "cp": {}, "echo": {}, "printf": {},
		"sleep": {}, "bash": {}, "sh": {}, "grep": {}, "test": {}, "[": {},
	}
	inUsr := map[string]struct{}{
		"find": {}, "file": {}, "chmod": {}, "chown": {}, "tee": {}, "whoami": {}, "id": {},
		"groups": {}, "hostname": {}, "uname": {}, "ps": {}, "top": {}, "env": {}, "printenv": {},
		"history": {}, "uptime": {}, "df": {}, "free": {}, "mount": {}, "which": {}, "type": {},
		"command": {}, "wget": {}, "curl": {}, "sudo": {}, "clear": {}, "head": {}, "tail": {},
		"wc": {}, "sort": {}, "uniq": {}, "base64": {}, "md5sum": {}, "sha256sum": {}, "date": {},
		"w": {}, "who": {}, "last": {}, "true": {}, "false": {}, "help": {}, "exit": {},
		"netstat": {}, "ss": {}, "ping": {}, "ssh": {}, "scp": {}, "readlink": {}, "stat": {},
		"tty": {},
	}
	inSbin := map[string]struct{}{"ip": {}, "ifconfig": {}}
	if _, ok := inBin[name]; ok {
		return "/bin/" + name
	}
	if _, ok := inUsr[name]; ok {
		return "/usr/bin/" + name
	}
	if _, ok := inSbin[name]; ok {
		return "/sbin/" + name
	}
	return ""
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

func (s *FakeShell) cmd_Env(args []string) string {
	s.Env["PWD"] = s.Cwd
	s.Env["USER"] = s.Username
	s.Env["HOME"] = s.Home
	s.Env["HOSTNAME"] = s.Hostname
	if len(args) > 0 {
		if val, ok := s.Env[args[0]]; ok {
			return val + "\n"
		}
		return ""
	}
	keys := make([]string, 0, len(s.Env))
	for key := range s.Env {
		keys = append(keys, key)
	}
	for i := 0; i < len(keys); i++ {
		for j := i + 1; j < len(keys); j++ {
			if keys[j] < keys[i] {
				keys[i], keys[j] = keys[j], keys[i]
			}
		}
	}
	var b strings.Builder
	for _, key := range keys {
		fmt.Fprintf(&b, "%s=%s\n", key, s.Env[key])
	}
	return b.String()
}

func (s *FakeShell) cmd_Export(args []string) string {
	if len(args) == 0 {
		return s.cmd_Env(nil)
	}
	for _, item := range args {
		if key, val, ok := strings.Cut(item, "="); ok {
			s.Env[key] = val
		}
	}
	return ""
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
	collect := func(full string) {
		var rest string
		if path == "/" {
			rest = full[1:]
		} else if full == path {
			return
		} else if strings.HasPrefix(full, prefix+"/") {
			rest = full[len(prefix)+1:]
		} else {
			return
		}
		add(strings.SplitN(rest, "/", 2)[0])
	}
	for full := range s.Tree {
		collect(full)
	}
	for full := range s.Binary {
		collect(full)
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
		path = s.resolve_Path(args[0])
	}
	long := has_Flag(parts, "l")
	withDot := has_Flag(parts, "a")
	_, inTree := s.Tree[path]
	_, inBin := s.Binary[path]
	if (inTree || inBin) && !s.is_Dir(path) {
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
	} else if data, ok := s.BinaryData[path]; ok {
		size = len(data)
		mode = "-rwxr-xr-x"
	} else if _, ok := s.Binary[path]; ok {
		size = 1024
		mode = "-rwxr-xr-x"
	}
	owner := "root"
	if strings.HasPrefix(path, s.Home) {
		owner = s.Username
	}
	meta := s.meta_Of(path)
	stamp := meta.mtime.Format("Jan _2 15:04")
	return fmt.Sprintf("%s 1 %s %s %8d %s %s", mode, owner, owner, size, stamp, name)
}

func (s *FakeShell) cmd_Cd(args []string) string {
	raw := s.Home
	if len(args) > 0 {
		raw = args[0]
	}
	path := s.resolve_Path(raw)
	_, inTree := s.Tree[path]
	_, inBin := s.Binary[path]
	if (inTree || inBin) && !s.is_Dir(path) {
		return fmt.Sprintf(texts.MsgShellNotDir, path)
	}
	if !s.is_Dir(path) {
		msg := fmt.Sprintf(texts.MsgShellNoFile, path)
		return strings.Replace(msg, "cat:", "cd:", 1)
	}
	s.Cwd = path
	s.Env["PWD"] = path
	return ""
}

func (s *FakeShell) cmd_Cat(args []string) string {
	if len(args) == 0 {
		return texts.MsgShellCatUsage
	}
	var b strings.Builder
	for _, arg := range args {
		path := s.resolve_Path(arg)
		if s.is_Dir(path) {
			return fmt.Sprintf(texts.MsgShellIsDir, path)
		}
		// Бинарники отдаём байтами - иначе ломается cat /proc/self/exe | head -c
		if data, ok := s.BinaryData[path]; ok {
			b.Write(data)
			continue
		}
		if _, isBin := s.Binary[path]; isBin {
			return fmt.Sprintf(texts.MsgShellBinary, path)
		}
		body, ok := s.Tree[path]
		if !ok {
			return fmt.Sprintf(texts.MsgShellNoFile, path)
		}
		b.WriteString(body)
	}
	return b.String()
}
