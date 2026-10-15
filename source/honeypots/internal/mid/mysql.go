package mid

import (
	"context"
	"crypto/rand"
	"crypto/sha1"
	"crypto/subtle"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"io"
	"net"
	"strings"

	"metricsd/internal/auth"
	"metricsd/internal/model"
	"metricsd/internal/texts"
)

const (
	mysqlCapConnectDB    = 1 << 3
	mysqlCapProtocol41   = 1 << 9
	mysqlCapSecure       = 1 << 15
	mysqlCapPluginAuth   = 1 << 19
	mysqlCapPluginLenenc = 1 << 21
	mysqlServerCaps      = 1 | 2 | 4 | mysqlCapConnectDB | mysqlCapProtocol41 | (1 << 13) | mysqlCapSecure | mysqlCapPluginAuth | mysqlCapPluginLenenc
	mysqlCmdQuit         = 0x01
	mysqlCmdQuery        = 0x03
	mysqlCmdInitDB       = 0x02
	mysqlCmdPing         = 0x0e
)

func Start_FakeMysql(
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
		version = "5.7.42-log"
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
		serve_Mysql(conn, session, version)
	})
}

func serve_Mysql(conn net.Conn, session dbSession, version string) {
	ip, sport := peerFromAddr(conn.RemoteAddr())
	session.emit_Connect(ip, sport)
	session.emit_Banner(ip, sport, "MySQL "+version)
	salt := make([]byte, 20)
	if _, err := rand.Read(salt); err != nil {
		return
	}
	if err := write_MysqlPacket(conn, 0, mysql_Greeting(version, salt)); err != nil {
		return
	}
	_, payload, err := read_MysqlPacket(conn)
	if err != nil {
		return
	}
	user, database, authBytes := parse_MysqlHandshake(payload)
	logged := mysql_LoggedSecret(authBytes)
	sourceIP := ""
	if ip != nil {
		sourceIP = *ip
	}
	success, plain := mysql_Accept(session, sourceIP, user, authBytes, salt)
	if plain != "" {
		logged = plain
	}
	session.emit_Auth(ip, sport, user, logged, database, success)
	if !success {
		_ = write_MysqlPacket(conn, 2, mysql_Error(1045, "28000", "Access denied for user"))
		return
	}
	if err := write_MysqlPacket(conn, 2, mysql_OK()); err != nil {
		return
	}
	if !session.Session.IsEnabled() {
		return
	}
	for {
		seq, packet, err := read_MysqlPacket(conn)
		if err != nil || len(packet) == 0 {
			return
		}
		switch packet[0] {
		case mysqlCmdQuit:
			return
		case mysqlCmdPing:
			if write_MysqlPacket(conn, seq+1, mysql_OK()) != nil {
				return
			}
		case mysqlCmdInitDB:
			database = strings.TrimRight(string(packet[1:]), "\x00")
			session.emit_Command(ip, sport, user, database, "USE "+database)
			if write_MysqlPacket(conn, seq+1, mysql_OK()) != nil {
				return
			}
		case mysqlCmdQuery:
			query := strings.TrimRight(string(packet[1:]), "\x00")
			session.emit_Command(ip, sport, user, database, query)
			if write_MysqlPacket(conn, seq+1, mysql_Error(1064, "42000", texts.MsgMysqlSyntax)) != nil {
				return
			}
		default:
			if write_MysqlPacket(conn, seq+1, mysql_Error(1064, "42000", texts.MsgMysqlSyntax)) != nil {
				return
			}
		}
	}
}

func mysql_Greeting(version string, salt []byte) []byte {
	body := []byte{10}
	body = append(body, []byte(version)...)
	body = append(body, 0)
	body = binary.LittleEndian.AppendUint32(body, 7)
	body = append(body, salt[:8]...)
	body = append(body, 0)
	caps := uint32(mysqlServerCaps)
	body = binary.LittleEndian.AppendUint16(body, uint16(caps))
	body = append(body, 33)
	body = binary.LittleEndian.AppendUint16(body, 2)
	body = binary.LittleEndian.AppendUint16(body, uint16(caps>>16))
	body = append(body, 21)
	body = append(body, make([]byte, 10)...)
	body = append(body, salt[8:]...)
	body = append(body, 0)
	body = append(body, []byte("mysql_native_password")...)
	body = append(body, 0)
	return body
}

func parse_MysqlHandshake(payload []byte) (string, string, []byte) {
	if len(payload) < 32 {
		return "", "", nil
	}
	caps := binary.LittleEndian.Uint32(payload[:4])
	pos := 4 + 4 + 1 + 23
	user, pos := mysql_CString(payload, pos)
	var authBytes []byte
	if caps&mysqlCapPluginLenenc != 0 {
		authBytes, pos = mysql_Lenenc(payload, pos)
	} else if caps&mysqlCapSecure != 0 && pos < len(payload) {
		n := int(payload[pos])
		pos++
		if pos+n <= len(payload) {
			authBytes = payload[pos : pos+n]
			pos += n
		}
	} else {
		authBytes, pos = mysql_CStringBytes(payload, pos)
	}
	database := ""
	if caps&mysqlCapConnectDB != 0 {
		database, _ = mysql_CString(payload, pos)
	}
	return user, database, authBytes
}

func mysql_CString(payload []byte, pos int) (string, int) {
	raw, next := mysql_CStringBytes(payload, pos)
	return string(raw), next
}

func mysql_CStringBytes(payload []byte, pos int) ([]byte, int) {
	if pos >= len(payload) {
		return nil, pos
	}
	end := pos
	for end < len(payload) && payload[end] != 0 {
		end++
	}
	next := end
	if end < len(payload) {
		next = end + 1
	}
	return payload[pos:end], next
}

func mysql_Lenenc(payload []byte, pos int) ([]byte, int) {
	if pos >= len(payload) {
		return nil, pos
	}
	lead := payload[pos]
	pos++
	n := 0
	switch {
	case lead < 251:
		n = int(lead)
	case lead == 0xfc && pos+2 <= len(payload):
		n = int(binary.LittleEndian.Uint16(payload[pos : pos+2]))
		pos += 2
	default:
		return nil, pos
	}
	if pos+n > len(payload) {
		return nil, len(payload)
	}
	return payload[pos : pos+n], pos + n
}

func mysql_LoggedSecret(authBytes []byte) string {
	if len(authBytes) == 20 {
		return hex.EncodeToString(authBytes)
	}
	return string(authBytes)
}

func mysql_Accept(
	session dbSession,
	sourceIP string,
	username string,
	authBytes []byte,
	salt []byte,
) (bool, string) {
	if !session.Auth.IsEnabled(true) || session.Auth.Mode == "" || session.Auth.Mode == auth.ModeAllowAll {
		return true, ""
	}
	if len(authBytes) != 20 {
		plain := string(authBytes)
		return session.accept_Login(sourceIP, username, plain), plain
	}
	matched := ""
	for _, credential := range session.Credentials {
		if credential.Username != username {
			continue
		}
		if mysql_NativeOK(credential.Password, salt, authBytes) {
			matched = credential.Password
			break
		}
	}
	if len(session.Auth.CredentialIDs) > 0 && matched == "" {
		return false, ""
	}
	password := matched
	if password == "" {
		password = hex.EncodeToString(authBytes)
	}
	return session.accept_Login(sourceIP, username, password), ""
}

// Клиент присылает хеш mysql_native_password, не сам пароль.
func mysql_NativeOK(password string, salt, clientAuth []byte) bool {
	if password == "" {
		return len(clientAuth) == 0
	}
	if len(clientAuth) != 20 || len(salt) < 20 {
		return false
	}
	first := sha1.Sum([]byte(password))
	second := sha1.Sum(first[:])
	mix := sha1.New()
	_, _ = mix.Write(salt[:20])
	_, _ = mix.Write(second[:])
	digest := mix.Sum(nil)
	for i := 0; i < 20; i++ {
		digest[i] ^= first[i]
	}
	return subtle.ConstantTimeCompare(digest, clientAuth) == 1
}

func mysql_OK() []byte {
	return []byte{0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00}
}

func mysql_Error(code int, state, message string) []byte {
	body := []byte{0xff}
	body = binary.LittleEndian.AppendUint16(body, uint16(code))
	body = append(body, '#')
	body = append(body, []byte(state)...)
	body = append(body, []byte(message)...)
	return body
}

func write_MysqlPacket(conn net.Conn, seq byte, payload []byte) error {
	head := []byte{byte(len(payload)), byte(len(payload) >> 8), byte(len(payload) >> 16), seq}
	if _, err := conn.Write(head); err != nil {
		return err
	}
	_, err := conn.Write(payload)
	return err
}

func read_MysqlPacket(conn net.Conn) (byte, []byte, error) {
	head := make([]byte, 4)
	if _, err := io.ReadFull(conn, head); err != nil {
		return 0, nil, err
	}
	size := int(head[0]) | int(head[1])<<8 | int(head[2])<<16
	if size > 1<<20 {
		return 0, nil, io.ErrUnexpectedEOF
	}
	payload := make([]byte, size)
	if size > 0 {
		if _, err := io.ReadFull(conn, payload); err != nil {
			return 0, nil, err
		}
	}
	return head[3], payload, nil
}
