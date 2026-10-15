package mid

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"net"
	"strconv"
	"strings"

	"metricsd/internal/auth"
	"metricsd/internal/model"
	"metricsd/internal/texts"
)

func Start_FakeRedis(
	ctx context.Context,
	port int,
	serviceID string,
	modules model.DbModules,
	credentials []model.CredentialBlock,
	store *auth.Store,
	onEvent EventHandler,
	debug bool,
	tokens *HoneytokenRegistry,
) error {
	version := strings.TrimSpace(modules.Banner.Version)
	if version == "" {
		version = "6.2.14"
	}
	session := dbSession{
		ServiceID:   serviceID,
		Port:        port,
		Auth:        modules.Auth,
		Session:     modules.Session,
		Credentials: credentials,
		Store:       store,
		OnEvent:     onEvent,
		Tokens:      tokens,
	}
	if debug {
		fmt.Printf(texts.MsgAgentServiceStart+"\n", serviceID, port)
	}
	return accept_Loop(ctx.Done(), port, func(conn net.Conn) {
		defer conn.Close()
		session.arm(conn)
		serve_Redis(conn, session, version)
	})
}

func serve_Redis(conn net.Conn, session dbSession, version string) {
	ip, sport := peerFromAddr(conn.RemoteAddr())
	session.emit_Connect(ip, sport)
	session.emit_Banner(ip, sport, "Redis "+version)
	reader := bufio.NewReader(conn)
	open := !session.Auth.IsEnabled(true)
	user := ""
	for {
		args, err := read_RedisCommand(reader)
		if err != nil || len(args) == 0 {
			return
		}
		name := strings.ToUpper(args[0])
		sourceIP := ""
		if ip != nil {
			sourceIP = *ip
		}
		switch name {
		case "QUIT":
			_, _ = conn.Write([]byte("+OK\r\n"))
			return
		case "PING":
			_, _ = conn.Write([]byte("+PONG\r\n"))
		case "AUTH":
			login, password := redis_Login(args[1:])
			if login == "default" {
				login = redis_UserForPassword(password, session)
			}
			success := session.accept_Login(sourceIP, login, password)
			session.emit_Auth(ip, sport, login, password, "0", success)
			if success {
				open = true
				user = login
				_, _ = conn.Write([]byte("+OK\r\n"))
			} else {
				_, _ = io.WriteString(conn, "-ERR "+texts.MsgRedisWrongPass+"\r\n")
			}
		default:
			if !open {
				_, _ = io.WriteString(conn, "-ERR "+texts.MsgRedisNoAuth+"\r\n")
				continue
			}
			if !session.Session.IsEnabled() {
				return
			}
			session.emit_Command(ip, sport, user, "0", strings.Join(args, " "))
			_, _ = conn.Write([]byte(redis_Reply(name, args[1:], version)))
		}
	}
}

func redis_Login(args []string) (string, string) {
	if len(args) >= 2 {
		return args[0], args[1]
	}
	if len(args) == 1 {
		return "default", args[0]
	}
	return "default", ""
}

func redis_UserForPassword(password string, session dbSession) string {
	for _, credential := range session.Credentials {
		if credential.Password == password && credential.Username != "" {
			return credential.Username
		}
	}
	return "default"
}

func redis_Reply(name string, args []string, version string) string {
	switch name {
	case "INFO":
		body := fmt.Sprintf(texts.MsgRedisInfo, version)
		return fmt.Sprintf("$%d\r\n%s\r\n", len(body), body)
	case "GET":
		return "$-1\r\n"
	case "KEYS", "SCAN":
		return "*0\r\n"
	case "DBSIZE":
		return ":0\r\n"
	case "HELLO":
		return "-ERR unknown command 'HELLO'\r\n"
	default:
		return "+OK\r\n"
	}
}

func read_RedisCommand(reader *bufio.Reader) ([]string, error) {
	lead, err := reader.ReadByte()
	if err != nil {
		return nil, err
	}
	if lead == '*' {
		line, err := reader.ReadString('\n')
		if err != nil {
			return nil, err
		}
		count, err := strconv.Atoi(strings.TrimSpace(line))
		if err != nil || count < 0 || count > 64 {
			return nil, io.ErrUnexpectedEOF
		}
		args := make([]string, 0, count)
		for i := 0; i < count; i++ {
			kind, err := reader.ReadByte()
			if err != nil {
				return nil, err
			}
			if kind != '$' {
				return nil, io.ErrUnexpectedEOF
			}
			sizeLine, err := reader.ReadString('\n')
			if err != nil {
				return nil, err
			}
			size, err := strconv.Atoi(strings.TrimSpace(sizeLine))
			if err != nil || size < 0 || size > 65536 {
				return nil, io.ErrUnexpectedEOF
			}
			buf := make([]byte, size+2)
			if _, err := io.ReadFull(reader, buf); err != nil {
				return nil, err
			}
			args = append(args, string(buf[:size]))
		}
		return args, nil
	}
	if err := reader.UnreadByte(); err != nil {
		return nil, err
	}
	line, err := reader.ReadString('\n')
	if err != nil {
		return nil, err
	}
	return strings.Fields(strings.TrimSpace(line)), nil
}
