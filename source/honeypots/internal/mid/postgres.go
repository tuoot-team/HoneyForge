package mid

import (
	"context"
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"strings"

	"metricsd/internal/auth"
	"metricsd/internal/model"
	"metricsd/internal/texts"
)

const (
	pgSSLRequest    = 80877103
	pgCancelRequest = 80877102
	pgProtocol30    = 196608
)

func Start_FakePostgres(
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
		version = "14.10 (Ubuntu 14.10-0ubuntu0.22.04.1)"
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
		serve_Postgres(conn, session, version)
	})
}

func serve_Postgres(conn net.Conn, session dbSession, version string) {
	ip, sport := peerFromAddr(conn.RemoteAddr())
	session.emit_Connect(ip, sport)
	session.emit_Banner(ip, sport, "PostgreSQL "+version)

	user, database, ok := read_PgStartup(conn)
	if !ok {
		return
	}
	if database == "" {
		database = user
	}
	if err := write_Pg(conn, 'R', pg_Int32(3)); err != nil {
		return
	}
	password, ok := read_PgPassword(conn)
	if !ok {
		return
	}
	sourceIP := ""
	if ip != nil {
		sourceIP = *ip
	}
	success := session.accept_Login(sourceIP, user, password)
	session.emit_Auth(ip, sport, user, password, database, success)
	if !success {
		_ = write_Pg(conn, 'E', pg_Error("FATAL", "28P01", fmt.Sprintf(texts.MsgPgAuthFail, user)))
		return
	}
	if err := write_PgReady(conn, version); err != nil {
		return
	}
	if !session.Session.IsEnabled() {
		return
	}
	for {
		tag, payload, err := read_PgMessage(conn)
		if err != nil {
			return
		}
		if tag == 'X' {
			return
		}
		if tag != 'Q' {
			_ = write_Pg(conn, 'E', pg_Error("ERROR", "08P01", "expected simple query"))
			_ = write_Pg(conn, 'Z', []byte{'I'})
			continue
		}
		query := strings.TrimRight(string(payload), "\x00")
		session.emit_Command(ip, sport, user, database, query)
		if strings.Contains(strings.ToLower(query), "version()") {
			_ = write_PgVersion(conn, version)
		} else {
			near := query
			if len(near) > 40 {
				near = near[:40]
			}
			_ = write_Pg(conn, 'E', pg_Error("ERROR", "42601", fmt.Sprintf(texts.MsgPgSyntax, near)))
		}
		if write_Pg(conn, 'Z', []byte{'I'}) != nil {
			return
		}
	}
}

func read_PgStartup(conn net.Conn) (string, string, bool) {
	for {
		body, err := read_PgStartupBody(conn)
		if err != nil || len(body) < 4 {
			return "", "", false
		}
		code := int(binary.BigEndian.Uint32(body[:4]))
		if code == pgSSLRequest {
			if _, err := conn.Write([]byte{'N'}); err != nil {
				return "", "", false
			}
			continue
		}
		if code == pgCancelRequest {
			return "", "", false
		}
		if code != pgProtocol30 {
			return "", "", false
		}
		fields := parse_PgFields(body[4:])
		return fields["user"], fields["database"], true
	}
}

func read_PgStartupBody(conn net.Conn) ([]byte, error) {
	head := make([]byte, 4)
	if _, err := io.ReadFull(conn, head); err != nil {
		return nil, err
	}
	size := int(binary.BigEndian.Uint32(head))
	if size < 8 || size > 65536 {
		return nil, io.ErrUnexpectedEOF
	}
	body := make([]byte, size-4)
	if _, err := io.ReadFull(conn, body); err != nil {
		return nil, err
	}
	return body, nil
}

func parse_PgFields(body []byte) map[string]string {
	fields := map[string]string{}
	parts := strings.Split(string(body), "\x00")
	for i := 0; i+1 < len(parts); i += 2 {
		if parts[i] == "" {
			break
		}
		fields[parts[i]] = parts[i+1]
	}
	return fields
}

func read_PgPassword(conn net.Conn) (string, bool) {
	tag, payload, err := read_PgMessage(conn)
	if err != nil || tag != 'p' {
		return "", false
	}
	return strings.TrimRight(string(payload), "\x00"), true
}

func read_PgMessage(conn net.Conn) (byte, []byte, error) {
	head := make([]byte, 5)
	if _, err := io.ReadFull(conn, head); err != nil {
		return 0, nil, err
	}
	size := int(binary.BigEndian.Uint32(head[1:5]))
	if size < 4 || size > 1<<20 {
		return 0, nil, io.ErrUnexpectedEOF
	}
	payload := make([]byte, size-4)
	if len(payload) > 0 {
		if _, err := io.ReadFull(conn, payload); err != nil {
			return 0, nil, err
		}
	}
	return head[0], payload, nil
}

func write_Pg(conn net.Conn, tag byte, payload []byte) error {
	frame := make([]byte, 5+len(payload))
	frame[0] = tag
	binary.BigEndian.PutUint32(frame[1:5], uint32(4+len(payload)))
	copy(frame[5:], payload)
	_, err := conn.Write(frame)
	return err
}

func write_PgReady(conn net.Conn, version string) error {
	params := [][2]string{
		{"server_version", version},
		{"server_encoding", "UTF8"},
		{"client_encoding", "UTF8"},
		{"DateStyle", "ISO, MDY"},
		{"integer_datetimes", "on"},
	}
	if err := write_Pg(conn, 'R', pg_Int32(0)); err != nil {
		return err
	}
	for _, pair := range params {
		body := append([]byte(pair[0]), 0)
		body = append(body, []byte(pair[1])...)
		body = append(body, 0)
		if err := write_Pg(conn, 'S', body); err != nil {
			return err
		}
	}
	key := make([]byte, 8)
	binary.BigEndian.PutUint32(key[:4], 1)
	binary.BigEndian.PutUint32(key[4:], 1)
	if err := write_Pg(conn, 'K', key); err != nil {
		return err
	}
	return write_Pg(conn, 'Z', []byte{'I'})
}

func write_PgVersion(conn net.Conn, version string) error {
	desc := []byte{}
	desc = append(desc, 0, 1)
	desc = append(desc, []byte("version")...)
	desc = append(desc, 0)
	desc = binary.BigEndian.AppendUint32(desc, 0)
	desc = binary.BigEndian.AppendUint16(desc, 0)
	desc = binary.BigEndian.AppendUint32(desc, 25)
	desc = binary.BigEndian.AppendUint16(desc, 65535)
	desc = binary.BigEndian.AppendUint32(desc, 0xffffffff)
	desc = binary.BigEndian.AppendUint16(desc, 0)
	if err := write_Pg(conn, 'T', desc); err != nil {
		return err
	}
	row := []byte{0, 1}
	row = binary.BigEndian.AppendUint32(row, uint32(len(version)))
	row = append(row, []byte(version)...)
	if err := write_Pg(conn, 'D', row); err != nil {
		return err
	}
	return write_Pg(conn, 'C', append([]byte("SELECT 1"), 0))
}

func pg_Error(severity, code, message string) []byte {
	body := []byte{}
	add := func(kind byte, value string) {
		body = append(body, kind)
		body = append(body, []byte(value)...)
		body = append(body, 0)
	}
	add('S', severity)
	add('V', severity)
	add('C', code)
	add('M', message)
	return append(body, 0)
}

func pg_Int32(value int) []byte {
	buf := make([]byte, 4)
	binary.BigEndian.PutUint32(buf, uint32(value))
	return buf
}
