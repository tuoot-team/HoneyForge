package mid

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/hex"
	"encoding/pem"
	"fmt"
	"io"
	mrand "math/rand"
	"net"
	"os"
	"path/filepath"
	"strings"
	"time"

	"golang.org/x/crypto/ssh"

	agentauth "honeyforge/honeypots/internal/auth"
	"honeyforge/honeypots/internal/model"
	"honeyforge/honeypots/internal/state"
	"honeyforge/honeypots/internal/texts"
)

func Is_SshBanner(banner string) bool {
	return strings.HasPrefix(strings.ToUpper(strings.TrimLeft(banner, " \t")), "SSH-")
}

func Format_SshBanner(version string) string {
	banner := strings.TrimSpace(version)
	if banner == "" {
		banner = "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"
	}
	if !strings.HasPrefix(strings.ToUpper(banner), "SSH-") {
		banner = "SSH-2.0-" + banner
	}
	return banner + "\r\n"
}

func Parse_ServerVersion(banner string) string {
	line := ""
	for _, raw := range strings.Split(banner, "\n") {
		if strings.TrimSpace(raw) != "" {
			line = strings.TrimSpace(raw)
			break
		}
	}
	line = strings.TrimSuffix(line, "\r")
	upper := strings.ToUpper(line)
	switch {
	case strings.HasPrefix(upper, "SSH-2.0-"):
		line = strings.TrimSpace(line[len("SSH-2.0-"):])
	case strings.HasPrefix(upper, "SSH-"):
		parts := strings.SplitN(line, "-", 3)
		if len(parts) == 3 {
			line = strings.TrimSpace(parts[2])
		}
	}
	if line == "" {
		return "OpenSSH_8.2p1"
	}
	return line
}

func Build_Hostname(seed string) string {
	cleaned := strings.TrimSpace(seed)
	if cleaned == "" {
		return "web-01"
	}
	sum := sha256.Sum256([]byte(cleaned))
	return "srv-" + hex.EncodeToString(sum[:])[:6]
}

func Pick_AuthDelay(delayMinMs, delayMaxMs int) time.Duration {
	low := delayMinMs
	high := delayMaxMs
	if low < 0 {
		low = 0
	}
	if high < 0 {
		high = 0
	}
	if high < low {
		low, high = high, low
	}
	if high <= 0 {
		return 0
	}
	ms := low
	if high > low {
		ms = low + mrand.Intn(high-low+1)
	}
	return time.Duration(ms) * time.Millisecond
}

func Load_HostKey(path string) (ssh.Signer, error) {
	if data, err := os.ReadFile(path); err == nil {
		signer, err := ssh.ParsePrivateKey(data)
		if err == nil {
			return signer, nil
		}
	}
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, err
	}
	signer, err := ssh.NewSignerFromKey(key)
	if err != nil {
		return nil, err
	}
	block := &pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: x509.MarshalPKCS1PrivateKey(key),
	}
	_ = os.MkdirAll(filepath.Dir(path), 0o755)
	_ = os.WriteFile(path, pem.EncodeToMemory(block), 0o600)
	return signer, nil
}

func Start_FakeSsh(
	ctx context.Context,
	port int,
	banner string,
	serviceName string,
	authModule model.AuthModule,
	shellModule model.ShellModule,
	credentials []model.CredentialBlock,
	authStore *agentauth.Store,
	seed string,
	hostKeyPath string,
	onEvent EventHandler,
	debug bool,
) error {
	hostname := Build_Hostname(seed)
	serverVersion := Parse_ServerVersion(banner)
	signer, err := Load_HostKey(hostKeyPath)
	if err != nil {
		return err
	}

	config := &ssh.ServerConfig{
		PasswordCallback: func(conn ssh.ConnMetadata, password []byte) (*ssh.Permissions, error) {
			delay := Pick_AuthDelay(authModule.DelayMsMin, authModule.DelayMsMax)
			if delay > 0 {
				time.Sleep(delay)
			}
			ip, sport := peerFromAddr(conn.RemoteAddr())
			sourceIP := ""
			if ip != nil {
				sourceIP = *ip
			}
			success := authStore.Evaluate(
				serviceName,
				sourceIP,
				conn.User(),
				string(password),
				authModule,
				credentials,
			)
			if debug && success {
				fmt.Printf(texts.MsgFakeSshAuth+"\n", conn.User(), derefStr(ip))
			}
			onEvent(model.AgentEvent{
				EventType:  "auth_attempt",
				SourceIP:   ip,
				SourcePort: sport,
				OccurredAt: state.Now_Iso(),
				Payload: map[string]any{
					"username": conn.User(),
					"password": string(password),
					"service":  serviceName,
					"success":  success,
				},
			})
			if !success {
				return nil, fmt.Errorf("permission denied")
			}
			return nil, nil
		},
		ServerVersion: "SSH-2.0-" + serverVersion,
	}
	config.AddHostKey(signer)

	addr := fmt.Sprintf("0.0.0.0:%d", port)
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return err
	}
	if debug {
		fmt.Printf(texts.MsgFakeSshStarted+"\n", port, hostname)
	}

	go func() {
		<-ctx.Done()
		_ = ln.Close()
	}()

	for {
		tcpConn, err := ln.Accept()
		if err != nil {
			select {
			case <-ctx.Done():
				return nil
			default:
				continue
			}
		}
		go serve_SSH(
			tcpConn,
			config,
			port,
			banner,
			serviceName,
			hostname,
			shellModule,
			onEvent,
			debug,
		)
	}
}

func serve_SSH(
	tcpConn net.Conn,
	config *ssh.ServerConfig,
	port int,
	banner string,
	serviceName string,
	hostname string,
	shellModule model.ShellModule,
	onEvent EventHandler,
	debug bool,
) {
	defer tcpConn.Close()
	ip, sport := peerFromAddr(tcpConn.RemoteAddr())
	if debug {
		fmt.Printf(texts.MsgLowConnect+"\n", derefStr(ip), derefInt(sport), port)
	}
	onEvent(model.AgentEvent{
		EventType:  "port_connect",
		SourceIP:   ip,
		SourcePort: sport,
		OccurredAt: state.Now_Iso(),
		Payload:    map[string]any{"port": port, "service": serviceName},
	})
	onEvent(model.AgentEvent{
		EventType:  "banner_grab",
		SourceIP:   ip,
		SourcePort: sport,
		OccurredAt: state.Now_Iso(),
		Payload: map[string]any{
			"port":   port,
			"banner": strings.TrimSpace(banner),
		},
	})

	sshConn, chans, reqs, err := ssh.NewServerConn(tcpConn, config)
	if err != nil {
		return
	}
	defer sshConn.Close()
	go ssh.DiscardRequests(reqs)

	for newChannel := range chans {
		if newChannel.ChannelType() != "session" {
			_ = newChannel.Reject(ssh.UnknownChannelType, "unknown channel type")
			continue
		}
		if !shellModule.IsEnabled() {
			_ = newChannel.Reject(ssh.Prohibited, "shell disabled")
			continue
		}
		channel, requests, err := newChannel.Accept()
		if err != nil {
			continue
		}
		go handle_Session(
			channel,
			requests,
			sshConn.User(),
			ip,
			sport,
			port,
			hostname,
			shellModule,
			onEvent,
		)
	}
}

func handle_Session(
	channel ssh.Channel,
	requests <-chan *ssh.Request,
	username string,
	sourceIP *string,
	sourcePort *int,
	port int,
	hostname string,
	shellModule model.ShellModule,
	onEvent EventHandler,
) {
	defer channel.Close()
	shell := New_FakeShell(
		username,
		hostname,
		shellModule.FsPack,
		sourceIP,
		sourcePort,
		port,
		onEvent,
	)

	for req := range requests {
		switch req.Type {
		case "pty-req", "env":
			if req.WantReply {
				_ = req.Reply(true, nil)
			}
		case "shell":
			if req.WantReply {
				_ = req.Reply(true, nil)
			}
			run_Shell(channel, shell, sourceIP, shellModule.MaxSessionSec)
			return
		case "exec":
			if req.WantReply {
				_ = req.Reply(true, nil)
			}
			cmd := parse_ExecPayload(req.Payload)
			out, _ := shell.Run_Line(cmd)
			_, _ = io.WriteString(channel, out)
			_, _ = channel.SendRequest("exit-status", false, ssh.Marshal(exitStatus{Status: 0}))
			return
		default:
			if req.WantReply {
				_ = req.Reply(false, nil)
			}
		}
	}
}

type exitStatus struct {
	Status uint32
}

// write_TTY: в SSH/PTY нужен CRLF, иначе курсор не возвращается в начало строки.
func write_TTY(w io.Writer, s string) {
	s = strings.ReplaceAll(s, "\r\n", "\n")
	s = strings.ReplaceAll(s, "\n", "\r\n")
	_, _ = io.WriteString(w, s)
}

func run_Shell(
	channel ssh.Channel,
	shell *FakeShell,
	sourceIP *string,
	maxSessionSec int,
) {
	ip := "?"
	if sourceIP != nil {
		ip = *sourceIP
	}
	write_TTY(channel, fmt.Sprintf(texts.MsgShellWelcome, shell.Hostname, ip))
	buf := make([]byte, 1)
	line := strings.Builder{}
	if maxSessionSec <= 0 {
		maxSessionSec = 600
	}
	sessionTimer := time.AfterFunc(
		time.Duration(maxSessionSec)*time.Second,
		func() { _ = channel.Close() },
	)
	defer sessionTimer.Stop()
	for {
		write_TTY(channel, shell.Prompt())
		line.Reset()
		for {
			n, err := channel.Read(buf)
			if n > 0 {
				ch := buf[0]
				if ch == '\r' || ch == '\n' {
					write_TTY(channel, "\n")
					break
				}
				if ch == 3 {
					write_TTY(channel, "^C\n")
					line.Reset()
					break
				}
				if ch == 127 || ch == 8 {
					if line.Len() > 0 {
						s := line.String()
						line.Reset()
						line.WriteString(s[:len(s)-1])
						_, _ = io.WriteString(channel, "\b \b")
					}
					continue
				}
				line.WriteByte(ch)
				_, _ = channel.Write(buf[:1])
			}
			if err != nil {
				return
			}
		}
		out, mustExit := shell.Run_Line(line.String())
		if out != "" {
			write_TTY(channel, out)
		}
		if mustExit {
			return
		}
	}
}

func parse_ExecPayload(payload []byte) string {
	if len(payload) < 4 {
		return string(payload)
	}
	n := int(payload[0])<<24 | int(payload[1])<<16 | int(payload[2])<<8 | int(payload[3])
	if 4+n > len(payload) {
		return string(payload[4:])
	}
	return string(payload[4 : 4+n])
}

func peerFromAddr(addr net.Addr) (*string, *int) {
	tcp, ok := addr.(*net.TCPAddr)
	if !ok || tcp == nil {
		return nil, nil
	}
	ip := tcp.IP.String()
	p := tcp.Port
	return &ip, &p
}

func derefStr(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}

func derefInt(p *int) any {
	if p == nil {
		return nil
	}
	return *p
}
