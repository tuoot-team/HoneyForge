package mid

import (
	"net"
	"strconv"
	"time"

	"metricsd/internal/auth"
	"metricsd/internal/model"
	"metricsd/internal/state"
)

type dbSession struct {
	ServiceID   string
	Port        int
	Auth        model.AuthModule
	Session     model.SessionModule
	Credentials []model.CredentialBlock
	Store       *auth.Store
	OnEvent     EventHandler
	Tokens      *HoneytokenRegistry
}

func (s dbSession) arm(conn net.Conn) {
	_ = conn.SetDeadline(time.Now().Add(time.Duration(s.Session.MaxSec()) * time.Second))
}

func (s dbSession) accept_Login(sourceIP, username, password string) bool {
	if !s.Auth.IsEnabled(true) {
		return true
	}
	delay := Pick_AuthDelay(s.Auth.DelayMsMin, s.Auth.DelayMsMax)
	if delay > 0 {
		time.Sleep(delay)
	}
	mode := s.Auth.Mode
	if mode == "" || mode == auth.ModeAllowAll {
		return true
	}
	if s.Store == nil {
		return false
	}
	return s.Store.Evaluate(s.ServiceID, sourceIP, username, password, s.Auth, s.Credentials)
}

func (s dbSession) emit(eventType string, ip *string, port *int, payload map[string]any) {
	if s.OnEvent == nil {
		return
	}
	s.OnEvent(model.AgentEvent{
		EventType:  eventType,
		SourceIP:   ip,
		SourcePort: port,
		OccurredAt: state.Now_Iso(),
		Payload:    payload,
	})
}

func (s dbSession) emit_Connect(ip *string, port *int) {
	s.emit("port_connect", ip, port, map[string]any{
		"port":    s.Port,
		"service": s.ServiceID,
	})
}

func (s dbSession) emit_Banner(ip *string, port *int, banner string) {
	s.emit("banner_grab", ip, port, map[string]any{
		"port":   s.Port,
		"banner": banner,
	})
}

func (s dbSession) emit_Auth(ip *string, port *int, username, password, database string, success bool) {
	s.emit("auth_attempt", ip, port, map[string]any{
		"username": username,
		"password": clip_Text(password, 200),
		"database": database,
		"service":  s.ServiceID,
		"success":  success,
	})
	if meta, ok := s.Tokens.Match_Cred(username, password); ok {
		Emit_HoneytokenHit(s.OnEvent, ip, port, meta, "auth", map[string]any{
			"service": s.ServiceID,
			"port":    s.Port,
		})
	}
}

func (s dbSession) emit_Command(ip *string, port *int, username, database, command string) {
	s.emit("db_command", ip, port, map[string]any{
		"username": username,
		"database": database,
		"command":  clip_Text(command, 200),
		"service":  s.ServiceID,
		"port":     s.Port,
	})
}

func clip_Text(value string, limit int) string {
	if len(value) <= limit {
		return value
	}
	return value[:limit]
}

func accept_Loop(ctxDone <-chan struct{}, port int, onConn func(net.Conn)) error {
	ln, err := listen_Port(port)
	if err != nil {
		return err
	}
	go func() {
		<-ctxDone
		_ = ln.Close()
	}()
	for {
		conn, err := ln.Accept()
		if err != nil {
			select {
			case <-ctxDone:
				return nil
			default:
				continue
			}
		}
		go onConn(conn)
	}
}

func listen_Port(port int) (net.Listener, error) {
	return net.Listen("tcp", net.JoinHostPort("0.0.0.0", strconv.Itoa(port)))
}
