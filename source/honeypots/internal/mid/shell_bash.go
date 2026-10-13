package mid

import (
	"fmt"
	"strconv"
	"strings"
	"unicode"
)

// expand_CommandLine - арифметика, $(), backticks, затем $VAR (один проход подстановок).
func (s *FakeShell) expand_CommandLine(line string) string {
	line = s.expand_Arith(line)
	line = s.expand_Subs(line)
	line = s.expand_Vars(line)
	return line
}

func (s *FakeShell) expand_Arith(raw string) string {
	var b strings.Builder
	for i := 0; i < len(raw); i++ {
		if i+2 < len(raw) && raw[i] == '$' && raw[i+1] == '(' && raw[i+2] == '(' {
			end := strings.Index(raw[i+3:], "))")
			if end < 0 {
				b.WriteByte(raw[i])
				continue
			}
			expr := raw[i+3 : i+3+end]
			b.WriteString(strconv.FormatInt(eval_Arith(expr), 10))
			i += 3 + end + 1 // до второго )
			continue
		}
		b.WriteByte(raw[i])
	}
	return b.String()
}

func eval_Arith(expr string) int64 {
	expr = strings.TrimSpace(expr)
	expr = strings.ReplaceAll(expr, " ", "")
	if expr == "" {
		return 0
	}
	// Простые + - * / слева направо по токенам чисел и ops
	var nums []int64
	var ops []byte
	i := 0
	for i < len(expr) {
		if expr[i] == '+' || expr[i] == '-' || expr[i] == '*' || expr[i] == '/' {
			ops = append(ops, expr[i])
			i++
			continue
		}
		j := i
		if j < len(expr) && (expr[j] == '+' || expr[j] == '-') && (j == i) {
			j++
		}
		for j < len(expr) && unicode.IsDigit(rune(expr[j])) {
			j++
		}
		n, _ := strconv.ParseInt(expr[i:j], 10, 64)
		nums = append(nums, n)
		i = j
	}
	if len(nums) == 0 {
		return 0
	}
	acc := nums[0]
	for k, op := range ops {
		if k+1 >= len(nums) {
			break
		}
		switch op {
		case '+':
			acc += nums[k+1]
		case '-':
			acc -= nums[k+1]
		case '*':
			acc *= nums[k+1]
		case '/':
			if nums[k+1] != 0 {
				acc /= nums[k+1]
			}
		}
	}
	return acc
}

func (s *FakeShell) expand_Subs(raw string) string {
	return s.expand_SubsDepth(raw, 0)
}

func (s *FakeShell) expand_SubsDepth(raw string, depth int) string {
	if depth > 2 {
		return raw
	}
	var b strings.Builder
	for i := 0; i < len(raw); i++ {
		if raw[i] == '`' {
			end := strings.IndexByte(raw[i+1:], '`')
			if end < 0 {
				b.WriteByte('`')
				continue
			}
			inner := s.prepare_Sub(raw[i+1:i+1+end], depth)
			out, _ := s.run_Pipes(strings.TrimSpace(inner))
			b.WriteString(strings.TrimRight(out, "\n"))
			i += 1 + end
			continue
		}
		if i+1 < len(raw) && raw[i] == '$' && raw[i+1] == '(' {
			if i+2 < len(raw) && raw[i+2] == '(' {
				b.WriteByte(raw[i])
				continue
			}
			nest := 1
			j := i + 2
			for j < len(raw) && nest > 0 {
				if raw[j] == '(' {
					nest++
				} else if raw[j] == ')' {
					nest--
				}
				j++
			}
			if nest != 0 {
				b.WriteByte(raw[i])
				continue
			}
			inner := s.prepare_Sub(raw[i+2:j-1], depth)
			out, _ := s.run_Pipes(strings.TrimSpace(inner))
			b.WriteString(strings.TrimRight(out, "\n"))
			i = j - 1
			continue
		}
		b.WriteByte(raw[i])
	}
	return b.String()
}

func (s *FakeShell) prepare_Sub(inner string, depth int) string {
	inner = s.expand_Arith(inner)
	inner = s.expand_SubsDepth(inner, depth+1)
	inner = s.expand_Vars(inner)
	return inner
}

func (s *FakeShell) expand_Globs(args []string) []string {
	var out []string
	for _, arg := range args {
		if !strings.ContainsAny(arg, "*?") {
			out = append(out, arg)
			continue
		}
		matches := s.glob_Match(arg)
		if len(matches) == 0 {
			out = append(out, arg)
			continue
		}
		out = append(out, matches...)
	}
	return out
}

func (s *FakeShell) glob_Match(pattern string) []string {
	dir := s.Cwd
	basePat := pattern
	if strings.Contains(pattern, "/") {
		slash := strings.LastIndex(pattern, "/")
		dirPart := pattern[:slash]
		if dirPart == "" {
			dir = "/"
		} else {
			dir = s.resolve_Path(dirPart)
		}
		basePat = pattern[slash+1:]
	}
	names := s.list_Names(dir, true)
	var matches []string
	for _, name := range names {
		if path_MatchSimple(basePat, name) {
			if dir == "/" {
				matches = append(matches, "/"+name)
			} else {
				matches = append(matches, dir+"/"+name)
			}
		}
	}
	return matches
}

func (s *FakeShell) cmd_Test(args []string) string {
	// Возвращает "" при успехе, иначе текст ошибки; код через command_Failed + специальный маркер
	ok, errMsg := s.eval_Test(args)
	if errMsg != "" {
		return errMsg
	}
	if ok {
		return ""
	}
	return "false: command failed\n"
}

func (s *FakeShell) eval_Test(args []string) (bool, string) {
	if len(args) == 0 {
		return false, ""
	}
	// Убрать закрывающую ]
	if args[len(args)-1] == "]" {
		args = args[:len(args)-1]
	}
	if len(args) == 0 {
		return false, ""
	}
	if len(args) == 1 {
		return args[0] != "", ""
	}
	if len(args) == 2 {
		op, val := args[0], args[1]
		switch op {
		case "-f":
			p := s.resolve_Path(val)
			return s.is_File(p) && !s.is_Dir(p), ""
		case "-d":
			return s.is_Dir(s.resolve_Path(val)), ""
		case "-e":
			return s.path_Exists(s.resolve_Path(val)), ""
		case "-z":
			return val == "", ""
		case "-n":
			return val != "", ""
		case "!":
			ok, err := s.eval_Test(args[1:])
			return !ok, err
		default:
			return false, fmt.Sprintf("test: %s: unary operator expected\n", op)
		}
	}
	if len(args) >= 3 {
		left, op, right := args[0], args[1], args[2]
		switch op {
		case "=", "==":
			return left == right, ""
		case "!=":
			return left != right, ""
		case "-eq":
			a, _ := strconv.Atoi(left)
			b, _ := strconv.Atoi(right)
			return a == b, ""
		case "-ne":
			a, _ := strconv.Atoi(left)
			b, _ := strconv.Atoi(right)
			return a != b, ""
		case "-lt":
			a, _ := strconv.Atoi(left)
			b, _ := strconv.Atoi(right)
			return a < b, ""
		case "-gt":
			a, _ := strconv.Atoi(left)
			b, _ := strconv.Atoi(right)
			return a > b, ""
		}
	}
	return false, ""
}
