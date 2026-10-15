package mid

import (
	"context"
	"crypto/ecdsa"
	"crypto/ed25519"
	"crypto/elliptic"
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

	agentauth "metricsd/internal/auth"
	"metricsd/internal/model"
	"metricsd/internal/state"
	"metricsd/internal/texts"
)

// Алгоритмы как у типичного OpenSSH 8.9 (без ML-KEM из дефолтов Go).
func openSshLikeAlgos() ssh.Config {
	return ssh.Config{
		KeyExchanges: []string{
			ssh.KeyExchangeCurve25519,
			"curve25519-sha256@libssh.org",
			ssh.KeyExchangeECDHP256,
			ssh.KeyExchangeECDHP384,
			ssh.KeyExchangeECDHP521,
			ssh.KeyExchangeDH14SHA256,
		},
		Ciphers: []string{
			ssh.CipherChaCha20Poly1305,
			ssh.CipherAES128GCM,
			ssh.CipherAES256GCM,
			ssh.CipherAES128CTR,
			ssh.CipherAES192CTR,
			ssh.CipherAES256CTR,
		},
		MACs: []string{
			ssh.HMACSHA256ETM,
			ssh.HMACSHA512ETM,
			ssh.HMACSHA256,
			ssh.HMACSHA512,
		},
	}
}

const defaultSshIdentification = "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"

func Is_SshBanner(banner string) bool {
	return strings.HasPrefix(strings.ToUpper(strings.TrimLeft(banner, " \t")), "SSH-")
}

// Ssh_Identification - строка RFC 4253 без CRLF; её же отдаём в crypto/ssh.ServerVersion.
func Ssh_Identification(version string) string {
	line := first_NonEmptyLine(version)
	if line == "" {
		return defaultSshIdentification
	}
	upper := strings.ToUpper(line)
	switch {
	case strings.HasPrefix(upper, "SSH-2.0-"):
		// Уже полный identification string.
	case strings.HasPrefix(upper, "SSH-1."):
		// Старый протокол не эмулируем - подменяем дефолтом OpenSSH 2.0.
		return defaultSshIdentification
	case strings.HasPrefix(upper, "SSH-"):
		// "SSH-2.0" без softwareversion - для nmap это softmatch Version=2.0.
		return defaultSshIdentification
	default:
		line = "SSH-2.0-" + line
	}
	if !ssh_SoftwareLooksReal(line) {
		return defaultSshIdentification
	}
	return line
}

func Format_SshBanner(version string) string {
	return Ssh_Identification(version) + "\r\n"
}

// Parse_ServerVersion оставляет softwareversion+comment для логов/тестов.
func Parse_ServerVersion(banner string) string {
	line := Ssh_Identification(banner)
	const prefix = "SSH-2.0-"
	if strings.HasPrefix(strings.ToUpper(line), prefix) {
		return strings.TrimSpace(line[len(prefix):])
	}
	return strings.TrimSpace(line)
}

func first_NonEmptyLine(raw string) string {
	for _, part := range strings.Split(raw, "\n") {
		line := strings.TrimSpace(strings.TrimSuffix(part, "\r"))
		if line != "" {
			return line
		}
	}
	return ""
}

// nmap softmatch SSH-([\d.]+)- даёт Version=2.0, если после префикса нет узнаваемого продукта.
func ssh_SoftwareLooksReal(identification string) bool {
	const prefix = "SSH-2.0-"
	if !strings.HasPrefix(strings.ToUpper(identification), prefix) {
		return false
	}
	software := strings.TrimSpace(identification[len(prefix):])
	if software == "" {
		return false
	}
	// "2.0" / "2" - только номер протокола, не продукт.
	if is_MostlyVersionNumber(software) {
		return false
	}
	for _, r := range software {
		if (r >= 'A' && r <= 'Z') || (r >= 'a' && r <= 'z') {
			return true
		}
	}
	return false
}

func is_MostlyVersionNumber(s string) bool {
	dot := false
	digit := false
	for _, r := range s {
		switch {
		case r >= '0' && r <= '9':
			digit = true
		case r == '.':
			dot = true
		default:
			return false
		}
	}
	return digit && (dot || len(s) <= 3)
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

func load_OrMake_Signer(path string, generate func() (ssh.Signer, []byte, error)) (ssh.Signer, error) {
	if data, err := os.ReadFile(path); err == nil {
		signer, err := ssh.ParsePrivateKey(data)
		if err == nil {
			return signer, nil
		}
	}
	signer, pemBytes, err := generate()
	if err != nil {
		return nil, err
	}
	_ = os.MkdirAll(filepath.Dir(path), 0o755)
	_ = os.WriteFile(path, pemBytes, 0o600)
	return signer, nil
}

func generate_RSA_HostKey() (ssh.Signer, []byte, error) {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, nil, err
	}
	signer, err := ssh.NewSignerFromKey(key)
	if err != nil {
		return nil, nil, err
	}
	block := &pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: x509.MarshalPKCS1PrivateKey(key),
	}
	return signer, pem.EncodeToMemory(block), nil
}

func generate_Ed25519_HostKey() (ssh.Signer, []byte, error) {
	_, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return nil, nil, err
	}
	signer, err := ssh.NewSignerFromKey(priv)
	if err != nil {
		return nil, nil, err
	}
	der, err := x509.MarshalPKCS8PrivateKey(priv)
	if err != nil {
		return nil, nil, err
	}
	block := &pem.Block{Type: "PRIVATE KEY", Bytes: der}
	return signer, pem.EncodeToMemory(block), nil
}

func generate_ECDSA_HostKey() (ssh.Signer, []byte, error) {
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return nil, nil, err
	}
	signer, err := ssh.NewSignerFromKey(key)
	if err != nil {
		return nil, nil, err
	}
	der, err := x509.MarshalECPrivateKey(key)
	if err != nil {
		return nil, nil, err
	}
	block := &pem.Block{Type: "EC PRIVATE KEY", Bytes: der}
	return signer, pem.EncodeToMemory(block), nil
}

// Load_HostKeys - ed25519 + ecdsa + rsa, как набор ключей Ubuntu OpenSSH.
func Load_HostKeys(basePath string) ([]ssh.Signer, error) {
	dir := filepath.Dir(basePath)
	edPath := filepath.Join(dir, ".ssh_host_ed25519")
	ecPath := filepath.Join(dir, ".ssh_host_ecdsa")
	rsaPath := basePath
	if filepath.Base(basePath) == ".ssh_host_key" {
		rsaPath = filepath.Join(dir, ".ssh_host_rsa")
		// Старый одиночный ключ - подхватить как RSA, если нового ещё нет.
		if _, err := os.Stat(rsaPath); err != nil {
			if _, errOld := os.Stat(basePath); errOld == nil {
				rsaPath = basePath
			}
		}
	}

	var signers []ssh.Signer
	ed, err := load_OrMake_Signer(edPath, generate_Ed25519_HostKey)
	if err != nil {
		return nil, err
	}
	signers = append(signers, ed)

	ec, err := load_OrMake_Signer(ecPath, generate_ECDSA_HostKey)
	if err != nil {
		return nil, err
	}
	signers = append(signers, ec)

	rsaSig, err := load_OrMake_Signer(rsaPath, generate_RSA_HostKey)
	if err != nil {
		return nil, err
	}
	signers = append(signers, rsaSig)
	return signers, nil
}

// Load_HostKey - совместимость: первый ключ из набора (ed25519).
func Load_HostKey(path string) (ssh.Signer, error) {
	signers, err := Load_HostKeys(path)
	if err != nil {
		return nil, err
	}
	if len(signers) == 0 {
		return nil, fmt.Errorf("no host keys")
	}
	return signers[0], nil
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
	loadPack LoadFsPackBytes,
	fileBaits map[string]string,
	tokens *HoneytokenRegistry,
) error {
	hostname := Build_Hostname(seed)
	// crypto/ssh сам допишет \r\n; сюда только identification без перевода строки.
	serverVersion := Ssh_Identification(banner)
	signers, err := Load_HostKeys(hostKeyPath)
	if err != nil {
		return err
	}

	config := &ssh.ServerConfig{
		Config: openSshLikeAlgos(),
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
			pass := string(password)
			success := authStore.Evaluate(
				serviceName,
				sourceIP,
				conn.User(),
				pass,
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
					"password": pass,
					"service":  serviceName,
					"success":  success,
				},
			})
			if meta, ok := tokens.Match_Cred(conn.User(), pass); ok {
				Emit_HoneytokenHit(onEvent, ip, sport, meta, "auth", map[string]any{
					"service": serviceName,
					"port":    port,
				})
			}
			if !success {
				return nil, fmt.Errorf("permission denied")
			}
			return nil, nil
		},
		ServerVersion: serverVersion,
	}
	for _, signer := range signers {
		config.AddHostKey(signer)
	}

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
			loadPack,
			fileBaits,
			tokens,
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
	loadPack LoadFsPackBytes,
	fileBaits map[string]string,
	tokens *HoneytokenRegistry,
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
			loadPack,
			fileBaits,
			tokens,
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
	loadPack LoadFsPackBytes,
	fileBaits map[string]string,
	tokens *HoneytokenRegistry,
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
		loadPack,
	)
	Apply_FileBaits(shell, fileBaits)
	Apply_HoneytokenFiles(shell, tokens)

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
	editor := ttyLineEditor{}
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
		editor.Reset()
		for {
			n, err := channel.Read(buf)
			if n > 0 {
				res := editor.Feed(buf[0])
				if res.Redraw {
					// Как bash: очистить экран и снова нарисовать prompt + текущий ввод.
					write_TTY(channel, "\033[H\033[2J")
					write_TTY(channel, shell.Prompt())
					if cur := editor.Content(); cur != "" {
						write_TTY(channel, cur)
					}
					continue
				}
				if res.Echo != "" {
					write_TTY(channel, res.Echo)
				}
				if res.Done {
					if !res.Cancel {
						out, mustExit := shell.Run_Line(res.Line)
						if out != "" {
							write_TTY(channel, out)
						}
						if mustExit {
							return
						}
					}
					break
				}
			}
			if err != nil {
				return
			}
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
