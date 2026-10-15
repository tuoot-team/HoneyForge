package agent

import (
	"context"
	"errors"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"

	agentauth "metricsd/internal/auth"
	"metricsd/internal/buffer"
	"metricsd/internal/client"
	"metricsd/internal/config"
	"metricsd/internal/low"
	"metricsd/internal/mid"
	"metricsd/internal/model"
	"metricsd/internal/state"
	"metricsd/internal/texts"
)

const (
	HeartbeatIntervalDefault = 30
	JitterPctDefault         = 30
	PairWaitSec              = 300
	PairPollSec              = 2
)

type Agent struct {
	BaseURL        string
	Debug          bool
	Root           string
	StatePath      string
	BufferPath     string
	HostKeyPath    string
	Client         *client.AgentClient
	Buffer         *buffer.EventBuffer
	AuthStore      *agentauth.Store
	Profile        model.Profile
	mu             sync.RWMutex
	restartMu      sync.Mutex
	servicesCancel context.CancelFunc
	servicesDone   chan struct{}
}

func New_Agent(root string) (*Agent, error) {
	config.Load_DotEnv(root)
	debug := config.Is_Debug()
	base := config.Get_BaseUrl()
	dataDir := config.Get_DataDir(root)
	bufPath := config.Get_BufferPath(root)
	eb, err := buffer.New_EventBuffer(bufPath, debug)
	if err != nil {
		return nil, err
	}
	return &Agent{
		BaseURL:     base,
		Debug:       debug,
		Root:        root,
		StatePath:   config.Get_StatePath(root),
		BufferPath:  bufPath,
		HostKeyPath: filepath.Join(dataDir, ".ssh_host_key"),
		Client:      client.New_AgentClient(base, debug),
		Buffer:      eb,
		AuthStore:   agentauth.New_Store(filepath.Join(dataDir, "auth_state.json")),
	}, nil
}

func (a *Agent) Close() {
	_ = a.Buffer.Close()
}

func (a *Agent) On_Event(ev model.AgentEvent) {
	logging := a.profile_Snapshot().Blocks.Logging
	if ev.Payload != nil {
		if !logging.Keeps_Credentials() {
			delete(ev.Payload, "password")
		}
		if !logging.Keeps_Payloads() {
			delete(ev.Payload, "command")
			delete(ev.Payload, "query")
		}
	}
	if !logging.Keeps_SourceMeta() {
		ev.SourceIP = nil
		ev.SourcePort = nil
	}
	if err := a.Buffer.Add(ev); err != nil && a.Debug {
		println("[DEBUG] buffer add:", err.Error())
	}
}

func (a *Agent) Ensure_Token() error {
	if !state.Has_Token(a.StatePath) {
		return fmt.Errorf("%s", texts.MsgErrNoToken)
	}
	token, _, err := state.Load_Token(a.StatePath)
	if err != nil {
		return err
	}
	a.Client.AgentToken = token
	return nil
}

func (a *Agent) Ensure_TokenOrPair(ctx context.Context) error {
	if state.Has_Token(a.StatePath) {
		return a.Ensure_Token()
	}
	fmt.Println(texts.MsgPairAutoStart)
	if err := a.Run_Pair(ctx); err != nil {
		return err
	}
	return a.Ensure_Token()
}

// Load_FsPack - скачать архив с центра, кэш рядом с data dir.
func (a *Agent) Load_FsPack(token string) ([]byte, error) {
	token = strings.TrimSpace(token)
	if token == "" {
		return nil, fmt.Errorf("пустой токен fs pack")
	}
	dataDir := config.Get_DataDir(a.Root)
	cacheDir := filepath.Join(dataDir, ".fs_packs")
	cachePath := filepath.Join(cacheDir, token)
	if raw, err := os.ReadFile(cachePath); err == nil && len(raw) > 0 {
		return raw, nil
	}
	raw, err := a.Client.Get_FsPackBytes(token)
	if err != nil {
		return nil, err
	}
	if err := os.MkdirAll(cacheDir, 0o755); err != nil {
		return raw, nil
	}
	_ = os.WriteFile(cachePath, raw, 0o600)
	return raw, nil
}

func (a *Agent) Load_Config() error {
	raw, err := a.Client.Get_Config()
	if err != nil {
		return err
	}
	if raw.Profile == nil {
		return fmt.Errorf("в ответе config нет profile")
	}
	a.mu.Lock()
	a.Profile = *raw.Profile
	a.mu.Unlock()
	mask := a.Profile.Blocks.Mask
	if mask.Mimicry.IsEnabled() && mask.Mimicry.UserAgent != "" {
		a.Client.UserAgent = mask.Mimicry.UserAgent
	} else {
		a.Client.UserAgent = ""
	}
	if mask.ProcessMask.IsEnabled() && mask.ProcessMask.Name != "" {
		Set_ProcessName(mask.ProcessMask.Name)
	}
	if a.Debug {
		config.Debug_Log(true, fmt.Sprintf("конфиг: %+v", a.Profile.Name))
	}
	return nil
}

func (a *Agent) profile_Snapshot() model.Profile {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return a.Profile
}

func (a *Agent) Run_Pair(ctx context.Context) error {
	started, err := a.Client.Start_Pairing()
	if err != nil {
		return err
	}
	fmt.Printf(texts.MsgPairStarted+"\n", started.DeviceCode)
	config.Debug_Log(a.Debug, fmt.Sprintf("pairing_id=%s expires_at=%s", started.PairingID, started.ExpiresAt))

	deadline := time.Now().Add(PairWaitSec * time.Second)
	attempt := 0
	for time.Now().Before(deadline) {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		attempt++
		result, err := a.Client.Try_Complete_Pairing(started.PairingID)
		if err != nil {
			return err
		}
		if result != nil {
			fmt.Printf(texts.MsgPairDone+"\n", result.TrapID)
			return state.Save_State(a.StatePath, result.TrapID, result.AgentToken)
		}
		fmt.Printf("\r"+texts.MsgPairWait, attempt)
		time.Sleep(PairPollSec * time.Second)
	}
	fmt.Println()
	return fmt.Errorf(texts.MsgPairTimeout, PairWaitSec, started.DeviceCode)
}

func cover_URLs(urls []string) []string {
	if len(urls) == 0 {
		return []string{"/favicon.ico", "/robots.txt"}
	}
	return urls
}

func (a *Agent) heartbeat_Loop(ctx context.Context) {
	for {
		profile := a.profile_Snapshot()
		mask := profile.Blocks.Mask
		interval := profile.MaskValue_Int("beacon_interval_sec", HeartbeatIntervalDefault)
		jitter := 0
		if mask.Jitter.IsEnabled() {
			jitter = profile.MaskValue_Int("jitter_pct", JitterPctDefault)
		}
		heartbeatPath := ""
		if mask.PathRotation.IsEnabled() {
			heartbeatPath = a.Client.Next_HeartbeatPath(mask.PathRotation.Paths)
		}

		result, err := a.Client.Post_Heartbeat(heartbeatPath, config.AgentVersion, map[string]any{
			"pid": os.Getpid(),
		})
		if err != nil {
			fmt.Printf("[WARN] heartbeat: %v\n", err)
		} else {
			fmt.Printf(texts.MsgHeartbeatOk+"\n", result.ConfigVersion)
		}

		if mask.Cover.IsEnabled() {
			for _, coverURL := range cover_URLs(mask.Cover.URLs) {
				a.Client.Get_Cover(coverURL)
			}
		}

		delta := interval * jitter / 100
		sleepFor := interval
		if delta > 0 {
			sleepFor = interval + rand.Intn(2*delta+1) - delta
		}
		if sleepFor < 5 {
			sleepFor = 5
		}
		select {
		case <-ctx.Done():
			return
		case <-time.After(time.Duration(sleepFor) * time.Second):
		}
	}
}

func (a *Agent) events_Loop(ctx context.Context) {
	for {
		pending, err := a.Buffer.Pending(200)
		if err != nil {
			fmt.Printf("[WARN] events: %v\n", err)
		} else if len(pending) > 0 {
			ids := make([]int64, len(pending))
			events := make([]model.AgentEvent, len(pending))
			for i, row := range pending {
				ids[i] = row.ID
				events[i] = row.Event
			}
			result, err := a.Client.Post_Events(events)
			if err != nil {
				fmt.Printf("[WARN] events: %v (события остаются в буфере)\n", err)
			} else {
				_ = a.Buffer.Mark_Sent(ids)
				fmt.Printf(texts.MsgEventsAccepted+"\n", result.Accepted)
			}
		}
		select {
		case <-ctx.Done():
			return
		case <-time.After(10 * time.Second):
		}
	}
}

func (a *Agent) claim_Loop(ctx context.Context) {
	a.claim_Loop_Interval(ctx, 15*time.Second)
}

func (a *Agent) claim_Loop_Slow(ctx context.Context) {
	// В courier-режиме реже ходим в центр (только management).
	a.claim_Loop_Interval(ctx, 5*time.Minute)
}

func (a *Agent) claim_Loop_Interval(ctx context.Context, every time.Duration) {
	for {
		out, err := a.Client.Claim_Commands()
		if err != nil {
			if a.Debug {
				println("[DEBUG] claim:", err.Error())
			}
		} else if out.Command != nil && out.Command.CommandType == "reload_config" {
			fmt.Println(texts.MsgAgentReload)
			if err := a.Load_Config(); err != nil {
				fmt.Printf("[WARN] reload_config: %v\n", err)
			} else {
				a.restart_Services(ctx)
			}
		}
		select {
		case <-ctx.Done():
			return
		case <-time.After(every):
		}
	}
}

func (a *Agent) restart_Services(parent context.Context) {
	a.restartMu.Lock()
	defer a.restartMu.Unlock()
	a.stop_ServicesLocked()
	svcCtx, cancel := context.WithCancel(parent)
	done := make(chan struct{})
	a.servicesCancel = cancel
	a.servicesDone = done
	go func() {
		defer close(done)
		a.run_Services(svcCtx)
	}()
}

func (a *Agent) stop_ServicesLocked() {
	if a.servicesCancel == nil {
		return
	}
	a.servicesCancel()
	<-a.servicesDone
	a.servicesCancel = nil
}

func (a *Agent) run_Services(ctx context.Context) {
	profile := a.profile_Snapshot()
	blocks := profile.Blocks
	seed := blocks.Mask.DecoyContentSeed
	// bait/tokens раскрываем один раз; FS-пути под юзера сессии - в Apply_* Home.
	expanded := mid.Expand_Baits(profile, "ops")
	tokens := mid.Expand_Honeytokens(profile, "ops")

	var wg sync.WaitGroup
	started := 0
	claimedPorts := map[int]string{}
	for _, svc := range blocks.Services {
		if !svc.IsEnabled() || svc.Port == 0 {
			continue
		}
		serviceID := svc.ID
		if serviceID == "" {
			serviceID = svc.Type
		}
		// Одна и та же пара порт/ловушка не должна глушить остальные сервисы.
		if owner, taken := claimedPorts[svc.Port]; taken {
			fmt.Printf(texts.MsgAgentPortDup+"\n", serviceID, svc.Port, owner)
			continue
		}
		claimedPorts[svc.Port] = serviceID
		fmt.Printf(texts.MsgAgentServiceStart+"\n", serviceID, svc.Port)
		started++
		port := svc.Port
		service := svc
		service.ID = serviceID
		wg.Add(1)
		go func() {
			defer wg.Done()
			var serviceErr error
			switch service.Type {
			case "ssh":
				// Что слушать, решают слоты, а не поле interaction_level.
				banner := mid.Format_SshBanner(service.SshModules.Banner.Version)
				if !service.SshModules.Auth.IsEnabled(true) {
					serviceErr = low.Start_TcpBanner(
						ctx,
						port,
						banner,
						service.ID,
						a.On_Event,
						a.Debug,
					)
					break
				}
				credentials := profile.CredentialsFor(
					service.SshModules.Auth.CredentialIDs,
				)
				serviceErr = mid.Start_FakeSsh(
					ctx,
					port,
					banner,
					service.ID,
					service.SshModules.Auth,
					service.SshModules.Shell,
					credentials,
					a.AuthStore,
					seed,
					a.HostKeyPath,
					a.On_Event,
					a.Debug,
					a.Load_FsPack,
					expanded.Files,
					tokens,
				)
			case "http":
				credentials := profile.CredentialsFor(
					service.HttpModules.Auth.CredentialIDs,
				)
				httpModules := mid.Merge_HttpBaitRoutes(
					service.HttpModules,
					expanded.HttpRoutes[service.ID],
				)
				httpModules = mid.Merge_HttpTokenRoutes(
					httpModules,
					tokens.PlantHTTP[service.ID],
				)
				serviceErr = mid.Start_FakeHttp(
					ctx,
					service.ID,
					port,
					httpModules,
					credentials,
					a.AuthStore,
					a.On_Event,
					a.Debug,
					tokens,
				)
			case "tcp_banner":
				serviceErr = low.Start_TcpBanner(
					ctx,
					port,
					service.TcpModules.Banner,
					service.ID,
					a.On_Event,
					a.Debug,
				)
			case "postgres":
				credentials := profile.CredentialsFor(service.PgModules.Auth.CredentialIDs)
				serviceErr = mid.Start_FakePostgres(
					ctx,
					port,
					service.ID,
					service.PgModules,
					credentials,
					a.AuthStore,
					a.On_Event,
					a.Debug,
					tokens,
				)
			case "redis":
				credentials := profile.CredentialsFor(service.RedisModules.Auth.CredentialIDs)
				serviceErr = mid.Start_FakeRedis(
					ctx,
					port,
					service.ID,
					service.RedisModules,
					credentials,
					a.AuthStore,
					a.On_Event,
					a.Debug,
					tokens,
				)
			case "mysql":
				credentials := profile.CredentialsFor(service.MysqlModules.Auth.CredentialIDs)
				serviceErr = mid.Start_FakeMysql(
					ctx,
					port,
					service.ID,
					service.MysqlModules,
					credentials,
					a.AuthStore,
					a.On_Event,
					a.Debug,
					tokens,
				)
			default:
				serviceErr = fmt.Errorf("неизвестный тип сервиса: %s", service.Type)
			}
			if serviceErr != nil && ctx.Err() == nil {
				if errors.Is(serviceErr, syscall.EADDRINUSE) {
					fmt.Printf(texts.MsgAgentPortBusy+"\n", service.ID, port)
				} else {
					fmt.Printf(texts.MsgAgentPortDenied+"\n", service.ID, port, serviceErr)
				}
			}
		}()
	}
	if started == 0 {
		fmt.Println(texts.MsgAgentNoServices)
		return
	}
	<-ctx.Done()
	wg.Wait()
}

func (a *Agent) Run(ctx context.Context) error {
	fmt.Printf(texts.MsgAgentStarted+"\n", config.AgentVersion)
	if err := a.Ensure_TokenOrPair(ctx); err != nil {
		return err
	}
	if err := a.Load_Config(); err != nil {
		return err
	}
	profile := a.profile_Snapshot()
	fmt.Printf(texts.MsgAgentConfigOk+"\n", profile.Name, profile.InteractionLevel)

	loopCtx, cancel := context.WithCancel(ctx)
	defer cancel()

	courierMode := profile.Blocks.Mask.IsCourierMode()
	if courierMode {
		// Курьер: без batch/heartbeat/cover; редкий claim+config для управления.
		fmt.Println(texts.MsgAgentCourierMode)
		go a.claim_Loop_Slow(loopCtx)
	} else {
		go a.heartbeat_Loop(loopCtx)
		go a.events_Loop(loopCtx)
		go a.claim_Loop(loopCtx)
	}
	a.restart_Services(loopCtx)

	<-ctx.Done()
	cancel()
	a.restartMu.Lock()
	a.stop_ServicesLocked()
	a.restartMu.Unlock()
	fmt.Println(texts.MsgAgentStopped)
	return nil
}

func Find_Root() string {
	if exePath, err := os.Executable(); err == nil {
		dir := filepath.Dir(exePath)
		if looks_LikeRoot(dir) {
			return dir
		}
		// go run кладёт бинарь во временную папку - пробуем cwd
	}
	if cwd, err := os.Getwd(); err == nil {
		if looks_LikeRoot(cwd) {
			return cwd
		}
		// если запуск из cmd/agent
		parent := filepath.Clean(filepath.Join(cwd, "../.."))
		if looks_LikeRoot(parent) {
			return parent
		}
	}
	return "."
}

func looks_LikeRoot(dir string) bool {
	_, err := os.Stat(filepath.Join(dir, "go.mod"))
	return err == nil
}
