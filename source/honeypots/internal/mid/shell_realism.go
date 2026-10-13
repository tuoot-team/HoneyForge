package mid

import (
	"fmt"
	"hash/fnv"
	"strconv"
	"strings"
	"time"
	"unicode"

	"honeyforge/honeypots/internal/texts"
)

const sleepMaxSec = 5

// Минимальный ELF64 stub: cat /proc/self/exe | head -c 22 должен видеть \x7fELF...
var elfStub = []byte{
	0x7f, 'E', 'L', 'F',
	2, 1, 1, 0,
	0, 0, 0, 0, 0, 0, 0, 0,
	2, 0, 0x3e, 0,
	1, 0, 0, 0,
	0, 0, 0, 0, 0, 0, 0, 0,
}

type fileMeta struct {
	inode uint32
	mtime time.Time
}

func (s *FakeShell) host_Seed() uint32 {
	h := fnv.New32a()
	_, _ = h.Write([]byte(s.Hostname + "|" + s.Username + "|" + s.Addr))
	return h.Sum32()
}

func (s *FakeShell) seed_RuntimeFs() {
	if s.BinaryData == nil {
		s.BinaryData = map[string][]byte{}
	}
	if s.Binary == nil {
		s.Binary = map[string]struct{}{}
	}
	if s.Dirs == nil {
		s.Dirs = map[string]struct{}{"/": {}}
	}
	if s.Meta == nil {
		s.Meta = map[string]fileMeta{}
	}
	seed := s.host_Seed()

	for _, dir := range []string{
		"/bin", "/sbin", "/usr", "/usr/bin", "/usr/sbin", "/usr/local", "/usr/local/bin",
		"/lib", "/lib64", "/proc", "/proc/self", "/sys", "/dev", "/dev/pts", "/run",
	} {
		s.Dirs[dir] = struct{}{}
		s.touch_Meta(dir, seed)
	}

	bins := []string{
		"/bin/bash", "/bin/sh", "/bin/ls", "/bin/cat", "/bin/echo", "/bin/pwd",
		"/bin/grep", "/bin/mkdir", "/bin/rm", "/bin/cp", "/bin/mv", "/bin/touch",
		"/bin/sleep", "/bin/test", "/bin/[",
		"/usr/bin/which", "/usr/bin/file", "/usr/bin/head", "/usr/bin/tail",
		"/usr/bin/wc", "/usr/bin/find", "/usr/bin/base64", "/usr/bin/md5sum",
		"/usr/bin/sha256sum", "/usr/bin/env", "/usr/bin/id", "/usr/bin/whoami",
		"/usr/bin/ps", "/usr/bin/top", "/usr/bin/free", "/usr/bin/df",
		"/usr/bin/curl", "/usr/bin/wget", "/usr/bin/sudo", "/usr/bin/ssh",
		"/usr/bin/netstat", "/usr/bin/ss", "/usr/bin/ping", "/usr/bin/readlink",
		"/usr/bin/stat", "/usr/bin/tty", "/usr/bin/command", "/usr/bin/type",
		"/sbin/ifconfig", "/usr/sbin/sshd",
	}
	for i, path := range bins {
		base := 110000 + int(seed%50000) + len(path)*13 + i*97
		s.put_Elf(path, base, seed+uint32(i)*2654435761)
	}
	s.put_Elf("/proc/self/exe", 900000+int(seed%200000), seed^0x0E1F)

	// /proc PIDs как у живой системы
	pids := []int{1, 2, 3, 100, 412, 700, 812, 850, 990}
	for _, pid := range pids {
		dir := fmt.Sprintf("/proc/%d", pid)
		s.Dirs[dir] = struct{}{}
		s.touch_Meta(dir, seed+uint32(pid))
	}
	s.Dirs["/proc/self"] = struct{}{}

	s.Tree["/proc/cpuinfo"] = texts.MsgShellCpuinfo
	s.Tree["/proc/meminfo"] = texts.MsgShellMeminfo
	s.Tree["/proc/version"] = fmt.Sprintf(texts.MsgShellUname, s.Hostname)
	s.Tree["/proc/self/cmdline"] = "bash\x00"
	s.Tree["/proc/self/comm"] = "bash\n"
	s.Tree["/proc/self/status"] = fmt.Sprintf(
		"Name:\tbash\nState:\tS (sleeping)\nTgid:\t990\nPid:\t990\nPPid:\t812\nUid:\t%s\t%s\t%s\t%s\n",
		s.uid_String(), s.uid_String(), s.uid_String(), s.uid_String(),
	)
	s.Tree["/proc/self/cwd"] = s.Cwd + "\n"
	s.Tree["/proc/1/cmdline"] = "/sbin/init\x00"
	s.Tree["/proc/1/comm"] = "systemd\n"
	s.Tree["/proc/1/status"] = "Name:\tsystemd\nState:\tS (sleeping)\nPid:\t1\n"
	s.Tree["/proc/812/cmdline"] = "/usr/sbin/sshd\x00-D\x00"
	s.Tree["/proc/812/comm"] = "sshd\n"
	s.Tree["/proc/990/cmdline"] = "-bash\x00"
	s.Tree["/proc/990/comm"] = "bash\n"

	gw := s.gateway_IP()
	s.Tree["/proc/net/route"] = fmt.Sprintf(
		"Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\n"+
			"eth0\t00000000\t%s\t0003\t0\t0\t100\t00000000\t0\t0\t0\n"+
			"eth0\t%s\t00000000\t0001\t0\t0\t0\t00FFFFFF\t0\t0\t0\n",
		ip_ToHexLE(gw), ip_ToHexLE(s.network_IP()),
	)
	add_ParentDirs(s.Dirs, "/proc/net/route")
	add_ParentDirs(s.Dirs, "/proc/self/status")
	add_ParentDirs(s.Dirs, "/proc/1/status")

	// /dev спецфайлы
	s.Tree["/dev/null"] = ""
	s.Tree["/dev/zero"] = ""
	s.Binary["/dev/urandom"] = struct{}{}
	s.BinaryData["/dev/urandom"] = s.pseudo_Random(256, seed^0x55AA)
	s.Dirs["/dev/pts"] = struct{}{}
	s.Tree["/dev/pts/0"] = ""
	for _, p := range []string{"/dev/null", "/dev/zero", "/dev/urandom", "/dev/pts/0"} {
		s.touch_Meta(p, seed)
		add_ParentDirs(s.Dirs, p)
	}

	// Метаданные для уже существующих текстовых файлов
	for path := range s.Tree {
		s.touch_Meta(path, seed)
	}
}

func (s *FakeShell) put_Elf(path string, size int, salt uint32) {
	if size < len(elfStub)+32 {
		size = len(elfStub) + 32
	}
	s.Binary[path] = struct{}{}
	data := make([]byte, size)
	copy(data, elfStub)
	// Хвост зависит от seed - разный md5sum на разных хостах
	for i := len(elfStub); i < len(data); i++ {
		data[i] = byte((uint32(i)*0x9E3779B9 ^ salt ^ uint32(i<<3)) % 251)
		if data[i] == 0 {
			data[i] = 1
		}
	}
	s.BinaryData[path] = data
	s.touch_Meta(path, salt)
	add_ParentDirs(s.Dirs, path)
}

func (s *FakeShell) touch_Meta(path string, salt uint32) {
	if s.Meta == nil {
		s.Meta = map[string]fileMeta{}
	}
	if _, ok := s.Meta[path]; ok {
		return
	}
	h := fnv.New32a()
	_, _ = h.Write([]byte(path))
	_, _ = h.Write([]byte{byte(salt), byte(salt >> 8), byte(salt >> 16), byte(salt >> 24)})
	n := h.Sum32()
	day := 1 + int(n%27)
	hour := int((n >> 5) % 24)
	min := int((n >> 11) % 60)
	mtime := time.Date(2026, time.September, day, hour, min, int(n%60), 0, time.UTC)
	s.Meta[path] = fileMeta{inode: 10000 + (n % 800000), mtime: mtime}
}

func (s *FakeShell) meta_Of(path string) fileMeta {
	if s.Meta != nil {
		if m, ok := s.Meta[path]; ok {
			return m
		}
	}
	s.touch_Meta(path, s.host_Seed())
	return s.Meta[path]
}

func (s *FakeShell) pseudo_Random(n int, salt uint32) []byte {
	out := make([]byte, n)
	x := salt | 1
	for i := 0; i < n; i++ {
		x = x*1664525 + 1013904223
		out[i] = byte(x >> 16)
	}
	return out
}

func (s *FakeShell) uid_String() string {
	if s.Username == "root" {
		return "0"
	}
	return "1000"
}

func (s *FakeShell) gateway_IP() string {
	if dot := strings.LastIndex(s.Addr, "."); dot > 0 {
		return s.Addr[:dot] + ".1"
	}
	return "10.0.0.1"
}

func (s *FakeShell) network_IP() string {
	if dot := strings.LastIndex(s.Addr, "."); dot > 0 {
		return s.Addr[:dot] + ".0"
	}
	return "10.0.0.0"
}

func ip_ToHexLE(ip string) string {
	parts := strings.Split(ip, ".")
	if len(parts) != 4 {
		return "0100000A"
	}
	var b [4]byte
	for i := 0; i < 4; i++ {
		n, _ := strconv.Atoi(parts[i])
		b[i] = byte(n)
	}
	return fmt.Sprintf("%02X%02X%02X%02X", b[0], b[1], b[2], b[3])
}

func (s *FakeShell) sync_EnvDefaults() {
	if s.Env == nil {
		s.Env = map[string]string{}
	}
	s.Env["USER"] = s.Username
	s.Env["LOGNAME"] = s.Username
	s.Env["HOME"] = s.Home
	s.Env["PWD"] = s.Cwd
	s.Env["SHELL"] = "/bin/bash"
	s.Env["HOSTNAME"] = s.Hostname
	s.Env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
	s.Env["TERM"] = "xterm-256color"
	s.Env["LANG"] = "en_US.UTF-8"
	s.Env["BASH"] = "/bin/bash"
	s.Env["BASH_VERSION"] = "5.1.16(1)-release"
	s.Env["BASH_VERSINFO"] = "5"
	s.Env["SHLVL"] = "1"
	s.Env["UID"] = s.uid_String()
	s.Env["EUID"] = s.uid_String()
	s.Env["OLDPWD"] = s.Home
	s.Env["_"] = "/bin/bash"
	s.Env["SSH_TTY"] = "/dev/pts/0"

	ip := "10.0.0.50"
	if s.SourceIP != nil && *s.SourceIP != "" {
		ip = *s.SourceIP
	}
	sport := 51234
	if s.SourcePort != nil && *s.SourcePort > 0 {
		sport = *s.SourcePort
	}
	lport := s.Port
	if lport == 0 {
		lport = 22
	}
	s.Env["SSH_CLIENT"] = fmt.Sprintf("%s %d %d", ip, sport, lport)
	s.Env["SSH_CONNECTION"] = fmt.Sprintf("%s %d %s %d", ip, sport, s.Addr, lport)
}

// expand_Vars - $VAR ${VAR} $0 $$ $?
func (s *FakeShell) expand_Vars(raw string) string {
	s.sync_EnvDefaults()
	var b strings.Builder
	for i := 0; i < len(raw); i++ {
		if raw[i] != '$' {
			b.WriteByte(raw[i])
			continue
		}
		if i+1 >= len(raw) {
			b.WriteByte('$')
			break
		}
		next := raw[i+1]
		switch next {
		case '$':
			b.WriteString("990")
			i++
		case '?':
			b.WriteString("0")
			i++
		case '0':
			b.WriteString("-bash")
			i++
		case '{':
			end := strings.IndexByte(raw[i+2:], '}')
			if end < 0 {
				b.WriteByte('$')
				continue
			}
			name := raw[i+2 : i+2+end]
			b.WriteString(s.lookup_Var(name))
			i += 2 + end
		case '(':
			// $(( или $( - оставляем для expand_Arith/Subs
			b.WriteByte('$')
		default:
			if unicode.IsLetter(rune(next)) || next == '_' {
				j := i + 1
				for j < len(raw) {
					ch := rune(raw[j])
					if unicode.IsLetter(ch) || unicode.IsDigit(ch) || ch == '_' {
						j++
						continue
					}
					break
				}
				b.WriteString(s.lookup_Var(raw[i+1 : j]))
				i = j - 1
			} else {
				b.WriteByte('$')
			}
		}
	}
	return b.String()
}

func (s *FakeShell) lookup_Var(name string) string {
	if name == "0" {
		return "-bash"
	}
	if val, ok := s.Env[name]; ok {
		return val
	}
	return ""
}

func (s *FakeShell) cmd_Ps(parts []string) string {
	user := s.Username
	if has_Flag(parts, "a") || has_Flag(parts, "u") || has_Flag(parts, "x") ||
		strings.Contains(strings.Join(parts, ""), "aux") ||
		strings.Contains(strings.Join(parts, ""), "ef") {
		return fmt.Sprintf(texts.MsgShellPsAux, user, user, user)
	}
	return texts.MsgShellPs
}

func (s *FakeShell) cmd_Netstat(parts []string) string {
	_ = parts
	return fmt.Sprintf(texts.MsgShellNetstat, s.Addr, s.Port)
}

func (s *FakeShell) cmd_Ping(args []string) string {
	host := net_Host(args)
	if host == "" {
		host = "8.8.8.8"
	}
	return fmt.Sprintf(texts.MsgShellPingFail, host, host, host)
}

func (s *FakeShell) cmd_Sleep(args []string) string {
	sec := 1.0
	if len(args) > 0 {
		if v, err := strconv.ParseFloat(args[0], 64); err == nil && v >= 0 {
			sec = v
		}
	}
	if sec > sleepMaxSec {
		sec = sleepMaxSec
	}
	time.Sleep(time.Duration(sec * float64(time.Second)))
	return ""
}

func (s *FakeShell) cmd_Readlink(parts []string, args []string) string {
	if len(args) == 0 {
		return fmt.Sprintf(texts.MsgShellNeedArg, "readlink")
	}
	full := s.resolve_Path(args[0])
	if full == "/proc/self/exe" || strings.HasSuffix(full, "/exe") && strings.Contains(full, "/proc/") {
		return "/bin/bash\n"
	}
	if full == "/proc/self/cwd" || strings.HasSuffix(full, "/cwd") {
		return s.Cwd + "\n"
	}
	if !s.path_Exists(full) {
		msg := fmt.Sprintf(texts.MsgShellNoFile, full)
		return strings.Replace(msg, "cat:", "readlink:", 1)
	}
	// Обычные файлы - не symlink
	if has_Flag(parts, "f") {
		return full + "\n"
	}
	return ""
}

func (s *FakeShell) cmd_Stat(args []string) string {
	if len(args) == 0 {
		return fmt.Sprintf(texts.MsgShellNeedArg, "stat")
	}
	var b strings.Builder
	for _, arg := range args {
		full := s.resolve_Path(arg)
		if !s.path_Exists(full) {
			msg := fmt.Sprintf(texts.MsgShellNoFile, full)
			return strings.Replace(msg, "cat:", "stat:", 1)
		}
		meta := s.meta_Of(full)
		size := 0
		ftype := "regular file"
		mode := "0644"
		human := "-rw-r--r--"
		if s.is_Dir(full) {
			ftype = "directory"
			size = 4096
			mode = "0755"
			human = "drwxr-xr-x"
		} else if data, ok := s.BinaryData[full]; ok {
			size = len(data)
			mode = "0755"
			human = "-rwxr-xr-x"
		} else if body, ok := s.Tree[full]; ok {
			size = len(body)
		}
		owner := s.Username
		uid := s.uid_String()
		if !strings.HasPrefix(full, s.Home) {
			owner = "root"
			uid = "0"
		}
		stamp := meta.mtime.Format("2006-01-02 15:04:05.000000000 +0000")
		blocks := (size + 511) / 512
		if blocks == 0 {
			blocks = 8
		}
		b.WriteString(fmt.Sprintf(
			texts.MsgShellStat,
			full, size, blocks, ftype, meta.inode,
			mode, human, uid, owner, uid, owner,
			stamp, stamp, stamp,
		))
	}
	return b.String()
}

func (s *FakeShell) cmd_IpRoute() string {
	gw := s.gateway_IP()
	net := s.network_IP()
	return fmt.Sprintf(
		"default via %s dev eth0 proto static \n%s/24 dev eth0 proto kernel scope link src %s \n",
		gw, net, s.Addr,
	)
}

func pipe_ByteCount(parts []string, fallback int) (int, bool) {
	pending := false
	for _, part := range parts[1:] {
		if part == "-c" || part == "--bytes" {
			pending = true
			continue
		}
		if pending || (strings.HasPrefix(part, "-c") && len(part) > 2) {
			raw := part
			if strings.HasPrefix(part, "-c") && len(part) > 2 {
				raw = part[2:]
			}
			n, err := strconv.Atoi(raw)
			if err == nil && n >= 0 {
				return n, true
			}
			pending = false
		}
	}
	return fallback, false
}
