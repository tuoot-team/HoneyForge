package mid

import (
	"fmt"
	"path"
	"strings"

	"honeyforge/honeypots/internal/texts"
)

// Все изменения Tree/Dirs/Binary живут только в этой сессии FakeShell
// и пропадают при disconnect (новый New_FakeShell на каждое подключение).

func (s *FakeShell) resolve_Path(raw string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return s.Cwd
	}
	if raw == "~" || strings.HasPrefix(raw, "~/") {
		raw = s.Home + raw[1:]
	}
	return normalize_Path(s.Cwd, raw)
}

func (s *FakeShell) path_Exists(full string) bool {
	if full == "/" || s.is_Dir(full) {
		return true
	}
	if _, ok := s.Tree[full]; ok {
		return true
	}
	if _, ok := s.BinaryData[full]; ok {
		return true
	}
	_, ok := s.Binary[full]
	return ok
}

func (s *FakeShell) is_File(full string) bool {
	if _, ok := s.Tree[full]; ok {
		return true
	}
	if _, ok := s.BinaryData[full]; ok {
		return true
	}
	_, ok := s.Binary[full]
	return ok
}

func (s *FakeShell) parent_Dir(full string) string {
	if full == "/" {
		return "/"
	}
	slash := strings.LastIndex(full, "/")
	if slash <= 0 {
		return "/"
	}
	return full[:slash]
}

func (s *FakeShell) ensure_Parent(full string) string {
	parent := s.parent_Dir(full)
	if !s.is_Dir(parent) {
		msg := fmt.Sprintf(texts.MsgShellNoFile, parent)
		return strings.Replace(msg, "cat:", "bash:", 1)
	}
	return ""
}

func (s *FakeShell) can_Write(full string) bool {
	if s.Username == "root" {
		return true
	}
	// Не-root пишет в home, /tmp, /var/tmp; /etc /bin /usr /root - нельзя
	if strings.HasPrefix(full, s.Home+"/") || full == s.Home {
		return true
	}
	if strings.HasPrefix(full, "/tmp/") || full == "/tmp" {
		return true
	}
	if strings.HasPrefix(full, "/var/tmp/") || full == "/var/tmp" {
		return true
	}
	if full == "/dev/null" || full == "/dev/zero" {
		return true
	}
	return false
}

func (s *FakeShell) write_TextFile(full string, body string) string {
	if full == "/dev/null" || full == "/dev/zero" {
		return ""
	}
	if errMsg := s.ensure_Parent(full); errMsg != "" {
		return errMsg
	}
	if s.is_Dir(full) {
		return fmt.Sprintf(texts.MsgShellIsDir, full)
	}
	if !s.can_Write(full) {
		return fmt.Sprintf(texts.MsgShellPermDeny, full)
	}
	delete(s.Binary, full)
	delete(s.BinaryData, full)
	s.Tree[full] = body
	add_ParentDirs(s.Dirs, full)
	s.touch_Meta(full, s.host_Seed())
	return ""
}

func (s *FakeShell) remove_Entry(full string, recursive bool) string {
	if full == "/" {
		return fmt.Sprintf(texts.MsgShellRmDir, full)
	}
	if !s.can_Write(full) {
		return fmt.Sprintf(texts.MsgShellPermDeny, full)
	}
	if s.is_Dir(full) {
		children := s.list_Names(full, true)
		if len(children) > 0 && !recursive {
			return fmt.Sprintf(texts.MsgShellRmDir, full)
		}
		if recursive {
			prefix := full + "/"
			for p := range s.Tree {
				if strings.HasPrefix(p, prefix) {
					delete(s.Tree, p)
				}
			}
			for p := range s.Binary {
				if strings.HasPrefix(p, prefix) {
					delete(s.Binary, p)
				}
			}
			for d := range s.Dirs {
				if d == full || strings.HasPrefix(d, prefix) {
					delete(s.Dirs, d)
				}
			}
		}
		delete(s.Dirs, full)
		return ""
	}
	if !s.is_File(full) {
		msg := fmt.Sprintf(texts.MsgShellNoFile, full)
		return strings.Replace(msg, "cat:", "rm:", 1)
	}
	delete(s.Tree, full)
	delete(s.Binary, full)
	return ""
}

func (s *FakeShell) cmd_Touch(args []string) string {
	if len(args) == 0 {
		return fmt.Sprintf(texts.MsgShellNeedArg, "touch")
	}
	for _, arg := range args {
		full := s.resolve_Path(arg)
		if s.is_Dir(full) {
			continue
		}
		if s.is_File(full) {
			continue
		}
		if errMsg := s.write_TextFile(full, ""); errMsg != "" {
			return errMsg
		}
	}
	return ""
}

func (s *FakeShell) cmd_Mkdir(parts []string, args []string) string {
	if len(args) == 0 {
		return fmt.Sprintf(texts.MsgShellNeedArg, "mkdir")
	}
	parents := has_Flag(parts, "p")
	for _, arg := range args {
		full := s.resolve_Path(arg)
		if !s.can_Write(full) {
			return fmt.Sprintf(texts.MsgShellPermDeny, full)
		}
		if s.path_Exists(full) {
			if s.is_Dir(full) && parents {
				continue
			}
			return fmt.Sprintf(texts.MsgShellExists, full)
		}
		if parents {
			cur := ""
			for _, part := range strings.Split(strings.Trim(full, "/"), "/") {
				if part == "" {
					continue
				}
				cur += "/" + part
				if s.is_File(cur) {
					return fmt.Sprintf("mkdir: cannot create directory ‘%s’: Not a directory\n", cur)
				}
				if s.is_Dir(cur) {
					continue
				}
				if !s.can_Write(cur) {
					return fmt.Sprintf(texts.MsgShellPermDeny, cur)
				}
				s.Dirs[cur] = struct{}{}
				s.touch_Meta(cur, s.host_Seed())
			}
			continue
		}
		parent := s.parent_Dir(full)
		if !s.is_Dir(parent) {
			msg := fmt.Sprintf(texts.MsgShellNoFile, parent)
			return strings.Replace(msg, "cat:", "mkdir:", 1)
		}
		s.Dirs[full] = struct{}{}
		s.touch_Meta(full, s.host_Seed())
	}
	return ""
}

func (s *FakeShell) cmd_Rmdir(args []string) string {
	if len(args) == 0 {
		return fmt.Sprintf(texts.MsgShellNeedArg, "rmdir")
	}
	for _, arg := range args {
		full := s.resolve_Path(arg)
		if !s.is_Dir(full) {
			msg := fmt.Sprintf(texts.MsgShellNoFile, full)
			return strings.Replace(msg, "cat:", "rmdir:", 1)
		}
		if len(s.list_Names(full, true)) > 0 {
			return fmt.Sprintf(texts.MsgShellNotEmpty, full)
		}
		delete(s.Dirs, full)
	}
	return ""
}

func (s *FakeShell) cmd_Rm(parts []string, args []string) string {
	if len(args) == 0 {
		return fmt.Sprintf(texts.MsgShellNeedArg, "rm")
	}
	recursive := has_Flag(parts, "r") || has_Flag(parts, "R")
	force := has_Flag(parts, "f")
	for _, arg := range args {
		full := s.resolve_Path(arg)
		if !s.path_Exists(full) {
			if force {
				continue
			}
			msg := fmt.Sprintf(texts.MsgShellNoFile, full)
			return strings.Replace(msg, "cat:", "rm:", 1)
		}
		if errMsg := s.remove_Entry(full, recursive); errMsg != "" {
			return errMsg
		}
	}
	return ""
}

func (s *FakeShell) copy_Node(src, dst string, recursive bool) string {
	if src == dst {
		return fmt.Sprintf(texts.MsgShellSameFile, "cp", src, dst)
	}
	if s.is_Dir(src) {
		if !recursive {
			return fmt.Sprintf("cp: -r not specified; omitting directory '%s'\n", src)
		}
		if errMsg := s.ensure_Parent(dst); errMsg != "" {
			return strings.Replace(errMsg, "bash:", "cp:", 1)
		}
		if s.is_File(dst) {
			return fmt.Sprintf("cp: cannot overwrite non-directory '%s' with directory '%s'\n", dst, src)
		}
		s.Dirs[dst] = struct{}{}
		prefix := src
		if src != "/" {
			prefix = src + "/"
		}
		for p, body := range s.Tree {
			if !strings.HasPrefix(p, prefix) && p != src {
				continue
			}
			rel := strings.TrimPrefix(p, src)
			target := path.Clean(dst + "/" + rel)
			s.Tree[target] = body
			add_ParentDirs(s.Dirs, target)
		}
		for p := range s.Binary {
			if !strings.HasPrefix(p, prefix) && p != src {
				continue
			}
			rel := strings.TrimPrefix(p, src)
			target := path.Clean(dst + "/" + rel)
			s.Binary[target] = struct{}{}
			add_ParentDirs(s.Dirs, target)
		}
		for d := range s.Dirs {
			if d == src || strings.HasPrefix(d, prefix) {
				rel := strings.TrimPrefix(d, src)
				target := path.Clean(dst + "/" + rel)
				s.Dirs[target] = struct{}{}
			}
		}
		return ""
	}
	if !s.is_File(src) {
		msg := fmt.Sprintf(texts.MsgShellNoFile, src)
		return strings.Replace(msg, "cat:", "cp:", 1)
	}
	target := dst
	if s.is_Dir(dst) {
		name := src[strings.LastIndex(src, "/")+1:]
		if dst == "/" {
			target = "/" + name
		} else {
			target = dst + "/" + name
		}
	}
	if body, ok := s.Tree[src]; ok {
		return s.write_TextFile(target, body)
	}
	if errMsg := s.ensure_Parent(target); errMsg != "" {
		return strings.Replace(errMsg, "bash:", "cp:", 1)
	}
	delete(s.Tree, target)
	s.Binary[target] = struct{}{}
	add_ParentDirs(s.Dirs, target)
	return ""
}

func (s *FakeShell) cmd_Cp(parts []string, args []string) string {
	if len(args) < 2 {
		return texts.MsgShellUsageCp
	}
	recursive := has_Flag(parts, "r") || has_Flag(parts, "R")
	dst := s.resolve_Path(args[len(args)-1])
	srcs := args[:len(args)-1]
	if len(srcs) > 1 && !s.is_Dir(dst) {
		return fmt.Sprintf("cp: target '%s' is not a directory\n", dst)
	}
	for _, arg := range srcs {
		src := s.resolve_Path(arg)
		if errMsg := s.copy_Node(src, dst, recursive); errMsg != "" {
			return errMsg
		}
	}
	return ""
}

func (s *FakeShell) move_Node(src, dst string) string {
	if src == dst {
		return fmt.Sprintf(texts.MsgShellSameFile, "mv", src, dst)
	}
	target := dst
	if s.is_Dir(dst) {
		name := src[strings.LastIndex(src, "/")+1:]
		if dst == "/" {
			target = "/" + name
		} else {
			target = dst + "/" + name
		}
	}
	if s.is_Dir(src) {
		if errMsg := s.copy_Node(src, target, true); errMsg != "" {
			return strings.Replace(errMsg, "cp:", "mv:", 1)
		}
		_ = s.remove_Entry(src, true)
		return ""
	}
	if !s.is_File(src) {
		msg := fmt.Sprintf(texts.MsgShellNoFile, src)
		return strings.Replace(msg, "cat:", "mv:", 1)
	}
	if body, ok := s.Tree[src]; ok {
		if errMsg := s.write_TextFile(target, body); errMsg != "" {
			return strings.Replace(errMsg, "cat:", "mv:", 1)
		}
		delete(s.Tree, src)
		return ""
	}
	if errMsg := s.ensure_Parent(target); errMsg != "" {
		return strings.Replace(errMsg, "bash:", "mv:", 1)
	}
	delete(s.Tree, target)
	s.Binary[target] = struct{}{}
	delete(s.Binary, src)
	add_ParentDirs(s.Dirs, target)
	return ""
}

func (s *FakeShell) cmd_Mv(args []string) string {
	if len(args) < 2 {
		return texts.MsgShellUsageMv
	}
	dst := s.resolve_Path(args[len(args)-1])
	srcs := args[:len(args)-1]
	if len(srcs) > 1 && !s.is_Dir(dst) {
		return fmt.Sprintf("mv: target '%s' is not a directory\n", dst)
	}
	for _, arg := range srcs {
		src := s.resolve_Path(arg)
		if errMsg := s.move_Node(src, dst); errMsg != "" {
			return errMsg
		}
	}
	return ""
}

func (s *FakeShell) cmd_Find(args []string) string {
	root := s.Cwd
	nameFilter := ""
	i := 0
	if len(args) > 0 && !strings.HasPrefix(args[0], "-") {
		root = s.resolve_Path(args[0])
		i = 1
	}
	for i < len(args) {
		if args[i] == "-name" && i+1 < len(args) {
			nameFilter = strings.Trim(args[i+1], `"'`)
			i += 2
			continue
		}
		i++
	}
	if !s.path_Exists(root) {
		msg := fmt.Sprintf(texts.MsgShellNoFile, root)
		return strings.Replace(msg, "cat:", "find:", 1)
	}
	var out []string
	match := func(full string) {
		base := full
		if slash := strings.LastIndex(full, "/"); slash >= 0 {
			base = full[slash+1:]
		}
		if nameFilter != "" && !path_MatchSimple(nameFilter, base) {
			return
		}
		out = append(out, full)
	}
	if s.is_Dir(root) {
		match(root)
	}
	prefix := root
	if root != "/" {
		prefix = root + "/"
	}
	for p := range s.Tree {
		if root == "/" || p == root || strings.HasPrefix(p, prefix) {
			match(p)
		}
	}
	for p := range s.Binary {
		if root == "/" || p == root || strings.HasPrefix(p, prefix) {
			match(p)
		}
	}
	for d := range s.Dirs {
		if d == root {
			continue
		}
		if root == "/" || strings.HasPrefix(d, prefix) {
			match(d)
		}
	}
	for i := 0; i < len(out); i++ {
		for j := i + 1; j < len(out); j++ {
			if out[j] < out[i] {
				out[i], out[j] = out[j], out[i]
			}
		}
	}
	if len(out) == 0 {
		return ""
	}
	return strings.Join(out, "\n") + "\n"
}

func path_MatchSimple(pattern, name string) bool {
	// Упрощённый glob: * и точное совпадение
	if pattern == "*" {
		return true
	}
	if !strings.Contains(pattern, "*") {
		return pattern == name
	}
	parts := strings.Split(pattern, "*")
	if !strings.HasPrefix(pattern, "*") && !strings.HasPrefix(name, parts[0]) {
		return false
	}
	rest := name
	for i, part := range parts {
		if part == "" {
			continue
		}
		idx := strings.Index(rest, part)
		if idx < 0 {
			return false
		}
		if i == 0 && !strings.HasPrefix(pattern, "*") && idx != 0 {
			return false
		}
		rest = rest[idx+len(part):]
	}
	if !strings.HasSuffix(pattern, "*") && len(parts) > 0 {
		last := parts[len(parts)-1]
		if last != "" && !strings.HasSuffix(name, last) {
			return false
		}
	}
	return true
}

func (s *FakeShell) cmd_File(args []string) string {
	if len(args) == 0 {
		return fmt.Sprintf(texts.MsgShellNeedArg, "file")
	}
	var b strings.Builder
	for _, arg := range args {
		full := s.resolve_Path(arg)
		_, isBin := s.Binary[full]
		_, hasData := s.BinaryData[full]
		switch {
		case s.is_Dir(full):
			b.WriteString(fmt.Sprintf(texts.MsgShellFileDir, full))
		case !s.path_Exists(full):
			msg := fmt.Sprintf(texts.MsgShellNoFile, full)
			b.WriteString(strings.Replace(msg, "cat:", "file:", 1))
		case isBin || hasData:
			b.WriteString(fmt.Sprintf(texts.MsgShellFileElf, full))
		default:
			body := s.Tree[full]
			if body == "" {
				b.WriteString(fmt.Sprintf(texts.MsgShellFileEmpty, full))
			} else {
				b.WriteString(fmt.Sprintf(texts.MsgShellFileText, full))
			}
		}
	}
	return b.String()
}

func (s *FakeShell) cmd_HeadTail(cmd string, parts []string, args []string) string {
	if len(args) == 0 {
		return fmt.Sprintf(texts.MsgShellNeedArg, cmd)
	}
	if nbytes, ok := pipe_ByteCount(parts, 0); ok {
		var b strings.Builder
		for _, arg := range args {
			full := s.resolve_Path(arg)
			body, errMsg := s.read_BytesAsString(full)
			if errMsg != "" {
				return strings.Replace(errMsg, "cat:", cmd+":", 1)
			}
			n := nbytes
			if cmd == "head" {
				if n > len(body) {
					n = len(body)
				}
				b.WriteString(body[:n])
			} else {
				if n > len(body) {
					n = len(body)
				}
				b.WriteString(body[len(body)-n:])
			}
		}
		return b.String()
	}
	limit := pipe_Count(parts, 10)
	var b strings.Builder
	for _, arg := range args {
		full := s.resolve_Path(arg)
		body, errMsg := s.read_BytesAsString(full)
		if errMsg != "" {
			return strings.Replace(errMsg, "cat:", cmd+":", 1)
		}
		rows := strings.Split(strings.TrimRight(body, "\n"), "\n")
		if body == "" {
			continue
		}
		n := limit
		if n > len(rows) {
			n = len(rows)
		}
		if cmd == "head" {
			b.WriteString(strings.Join(rows[:n], "\n") + "\n")
		} else {
			b.WriteString(strings.Join(rows[len(rows)-n:], "\n") + "\n")
		}
	}
	return b.String()
}

func (s *FakeShell) read_BytesAsString(full string) (string, string) {
	if s.is_Dir(full) {
		return "", fmt.Sprintf(texts.MsgShellIsDir, full)
	}
	if data, ok := s.BinaryData[full]; ok {
		return string(data), ""
	}
	if _, ok := s.Binary[full]; ok {
		return "", fmt.Sprintf(texts.MsgShellBinary, full)
	}
	body, ok := s.Tree[full]
	if !ok {
		return "", fmt.Sprintf(texts.MsgShellNoFile, full)
	}
	return body, ""
}

func (s *FakeShell) cmd_Tee(parts []string, args []string, stdin string) string {
	appendMode := has_Flag(parts, "a")
	if len(args) == 0 {
		return stdin
	}
	for _, arg := range args {
		full := s.resolve_Path(arg)
		body := stdin
		if appendMode {
			if prev, ok := s.Tree[full]; ok {
				body = prev + stdin
			}
		}
		if errMsg := s.write_TextFile(full, body); errMsg != "" {
			return errMsg
		}
	}
	return stdin
}
