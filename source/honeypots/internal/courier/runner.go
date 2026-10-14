package courier

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strings"
	"time"

	"golang.org/x/crypto/ssh"

	"honeyforge/honeypots/internal/config"
	"honeyforge/honeypots/internal/model"
	"honeyforge/honeypots/internal/state"
	"honeyforge/honeypots/internal/texts"
)

const (
	PairWaitSec   = 900
	PairPollSec   = 2
	ClaimEverySec = 20
)

type Runner struct {
	Client    *Client
	StatePath string
	Debug     bool
}

func New_Runner(root string) (*Runner, error) {
	debug := config.Is_Debug()
	return &Runner{
		Client:    New_Client(config.Get_BaseUrl(), debug),
		StatePath: filepath.Join(root, ".courier_state.json"),
		Debug:     debug,
	}, nil
}

func (r *Runner) Ensure_TokenOrPair(ctx context.Context) error {
	if state.Has_Token(r.StatePath) {
		token, _, err := state.Load_Token(r.StatePath)
		if err != nil {
			return err
		}
		r.Client.CourierToken = token
		return nil
	}
	fmt.Println(texts.MsgPairAutoStart)
	return r.Run_Pair(ctx)
}

func (r *Runner) Run_Pair(ctx context.Context) error {
	started, err := r.Client.Start_Pairing()
	if err != nil {
		return err
	}
	fmt.Printf(texts.MsgCourierPairStart+"\n", started.DeviceCode)

	deadline := time.Now().Add(PairWaitSec * time.Second)
	attempt := 0
	for time.Now().Before(deadline) {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		attempt++
		result, err := r.Client.Try_Complete_Pairing(started.PairingID)
		if err != nil {
			return err
		}
		if result != nil {
			fmt.Printf(texts.MsgCourierPairDone+"\n", result.CourierID)
			r.Client.CourierToken = result.CourierToken
			return state.Save_State(r.StatePath, result.CourierID, result.CourierToken)
		}
		fmt.Printf("\r"+texts.MsgPairWait, attempt)
		time.Sleep(PairPollSec * time.Second)
	}
	fmt.Println()
	return fmt.Errorf(texts.MsgPairTimeout, PairWaitSec, started.DeviceCode)
}

func (r *Runner) Run(ctx context.Context) error {
	fmt.Printf(texts.MsgCourierStarted+"\n", config.AgentVersion)
	if err := r.Ensure_TokenOrPair(ctx); err != nil {
		return err
	}
	_ = r.Client.Get_Config()

	for {
		select {
		case <-ctx.Done():
			return nil
		default:
		}
		if err := r.do_One_Visit(ctx); err != nil {
			fmt.Printf(texts.MsgCourierVisitFail+"\n", err)
		}
		select {
		case <-ctx.Done():
			return nil
		case <-time.After(ClaimEverySec * time.Second):
		}
	}
}

type remoteBufferStore struct {
	NextID int64 `json:"next_id"`
	Events []struct {
		ID      int64            `json:"id"`
		Payload model.AgentEvent `json:"payload"`
		Sent    bool             `json:"sent"`
	} `json:"events"`
}

func (r *Runner) do_One_Visit(_ context.Context) error {
	claim, err := r.Client.Claim_Visit()
	if err != nil {
		return err
	}
	if claim.VisitID == nil || claim.SSH == nil || claim.BufferPath == nil {
		fmt.Println(texts.MsgCourierVisitSkip)
		return nil
	}
	visitID := *claim.VisitID
	bufferPath := *claim.BufferPath

	// Сначала только читаем буфер. Wipe - только после успешной сдачи в ядро,
	// иначе при сетевом сбое на complete события пропадут навсегда.
	conn, events, nextID, err := pull_Buffer(claim.SSH, bufferPath, r.Debug)
	if err != nil {
		errText := err.Error()
		_, _ = r.Client.Complete_Visit(visitID, VisitCompleteIn{
			OK:    false,
			Error: &errText,
		})
		return err
	}
	defer conn.Close()

	out, err := r.Client.Complete_Visit(visitID, VisitCompleteIn{
		OK:     true,
		Events: events,
	})
	if err != nil {
		// Буфер не трогали - следующий визит повторит съём.
		return err
	}
	if wipeErr := wipe_Buffer(conn, bufferPath, nextID); wipeErr != nil {
		fmt.Printf(texts.MsgCourierWipeWarn+"\n", wipeErr)
	}
	fmt.Printf(texts.MsgCourierVisitOk+"\n", visitID, out.Accepted)
	return nil
}

func dial_Trap_SSH(sshCfg map[string]any, debug bool) (*ssh.Client, error) {
	host, _ := sshCfg["host"].(string)
	user, _ := sshCfg["user"].(string)
	port := 22
	switch v := sshCfg["port"].(type) {
	case float64:
		port = int(v)
	case int:
		port = v
	}
	password, _ := sshCfg["password"].(string)
	privateKey, _ := sshCfg["private_key"].(string)
	if host == "" || user == "" {
		return nil, fmt.Errorf(texts.MsgCourierSshBad)
	}

	auth := []ssh.AuthMethod{}
	if privateKey != "" {
		signer, err := ssh.ParsePrivateKey([]byte(privateKey))
		if err != nil {
			return nil, fmt.Errorf(texts.MsgCourierKeyBad, err)
		}
		auth = append(auth, ssh.PublicKeys(signer))
	}
	if password != "" {
		auth = append(auth, ssh.Password(password))
	}
	if len(auth) == 0 {
		return nil, fmt.Errorf(texts.MsgCourierSshNoAuth)
	}

	configSSH := &ssh.ClientConfig{
		User:            user,
		Auth:            auth,
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
		Timeout:         20 * time.Second,
	}
	addr := net.JoinHostPort(host, fmt.Sprintf("%d", port))
	if debug {
		println("[DEBUG] courier ssh", addr)
	}
	return ssh.Dial("tcp", addr, configSSH)
}

func pull_Buffer(
	sshCfg map[string]any,
	bufferPath string,
	debug bool,
) (*ssh.Client, []VisitEventIn, int64, error) {
	conn, err := dial_Trap_SSH(sshCfg, debug)
	if err != nil {
		return nil, nil, 1, err
	}

	raw, err := ssh_Run(conn, fmt.Sprintf("cat %s 2>/dev/null || true", shell_Quote(bufferPath)))
	if err != nil {
		conn.Close()
		return nil, nil, 1, err
	}

	nextID := int64(1)
	events := []VisitEventIn{}
	if strings.TrimSpace(raw) != "" {
		var store remoteBufferStore
		if err := json.Unmarshal([]byte(raw), &store); err != nil {
			conn.Close()
			return nil, nil, 1, fmt.Errorf(texts.MsgCourierBufParse, err)
		}
		if store.NextID > 1 {
			nextID = store.NextID
		}
		for _, row := range store.Events {
			if row.Sent {
				continue
			}
			id := row.ID
			if id >= nextID {
				nextID = id + 1
			}
			payload := row.Payload.Payload
			if payload == nil {
				payload = map[string]any{}
			}
			ev := VisitEventIn{
				EventType:     row.Payload.EventType,
				SourceIP:      row.Payload.SourceIP,
				SourcePort:    row.Payload.SourcePort,
				Payload:       payload,
				AgentBufferID: &id,
			}
			if row.Payload.OccurredAt != "" {
				oa := row.Payload.OccurredAt
				ev.OccurredAt = &oa
			}
			events = append(events, ev)
		}
	}
	return conn, events, nextID, nil
}

func wipe_Buffer(conn *ssh.Client, bufferPath string, nextID int64) error {
	// next_id сохраняем: иначе новые события получат старые id и дедуп в ядре их отбросит.
	if nextID < 1 {
		nextID = 1
	}
	empty := fmt.Sprintf(`{"next_id":%d,"events":[]}`, nextID)
	wipeCmd := fmt.Sprintf(
		"printf '%%s\\n' %s > %s && rm -f /tmp/hf-courier-* 2>/dev/null || true",
		shell_Quote(empty),
		shell_Quote(bufferPath),
	)
	_, err := ssh_Run(conn, wipeCmd)
	if err != nil {
		return fmt.Errorf(texts.MsgCourierWipeFail, err)
	}
	return nil
}

func ssh_Run(conn *ssh.Client, cmd string) (string, error) {
	session, err := conn.NewSession()
	if err != nil {
		return "", err
	}
	defer session.Close()
	var stdout, stderr strings.Builder
	session.Stdout = &stdout
	session.Stderr = &stderr
	if err := session.Run(cmd); err != nil {
		return "", fmt.Errorf("%w: %s", err, stderr.String())
	}
	return stdout.String(), nil
}

func shell_Quote(s string) string {
	return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
}

func Find_Root() string {
	if exePath, err := os.Executable(); err == nil {
		dir := filepath.Dir(exePath)
		if looks_LikeRoot(dir) {
			return dir
		}
	}
	if cwd, err := os.Getwd(); err == nil {
		if looks_LikeRoot(cwd) {
			return cwd
		}
		parent := filepath.Clean(filepath.Join(cwd, "../.."))
		if looks_LikeRoot(parent) {
			return parent
		}
	}
	return "."
}

func looks_LikeRoot(dir string) bool {
	if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
		return true
	}
	if _, err := os.Stat(filepath.Join(dir, ".env")); err == nil {
		return true
	}
	return false
}
