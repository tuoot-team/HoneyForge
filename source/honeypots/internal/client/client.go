package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"honeyforge/honeypots/internal/model"
	"honeyforge/honeypots/internal/texts"
)

const (
	AgentHeader = "X-Agent-Token"

	PathPairingStart       = "/api/v1/pairing/start"
	PathPairingComplete    = "/api/v1/pairing/%s/complete"
	PathAgentConfig        = "/api/v1/agent/config"
	PathAgentHeartbeat     = "/api/v1/agent/heartbeat"
	PathAgentEvents        = "/api/v1/agent/events"
	PathAgentCommandsClaim = "/api/v1/agent/commands/claim"
	PathAgentFsPack        = "/api/v1/agent/fs-packs/%s"
)

type AgentClient struct {
	BaseURL    string
	AgentToken string
	Debug      bool
	UserAgent  string
	HTTPClient *http.Client
	pathCursor int
}

func New_AgentClient(baseURL string, debug bool) *AgentClient {
	return &AgentClient{
		BaseURL: strings.TrimRight(baseURL, "/"),
		Debug:   debug,
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (c *AgentClient) debug_Log(message string) {
	if c.Debug {
		println("[DEBUG]", message)
	}
}

func (c *AgentClient) headers(agent bool) (http.Header, error) {
	h := make(http.Header)
	h.Set("Accept", "application/json")
	if c.UserAgent != "" {
		h.Set("User-Agent", c.UserAgent)
	}
	if agent {
		if c.AgentToken == "" {
			return nil, fmt.Errorf("%s", texts.MsgErrNoTokenClient)
		}
		h.Set(AgentHeader, c.AgentToken)
	}
	return h, nil
}

func (c *AgentClient) request_JSON(
	method, path string,
	jsonBody any,
	agent bool,
	okStatuses ...int,
) (json.RawMessage, error) {
	if len(okStatuses) == 0 {
		okStatuses = []int{200, 201}
	}
	url := c.BaseURL + path
	c.debug_Log(fmt.Sprintf(texts.MsgDebugRequest, method, url))

	var bodyReader io.Reader
	if jsonBody != nil {
		raw, err := json.Marshal(jsonBody)
		if err != nil {
			return nil, err
		}
		bodyReader = bytes.NewReader(raw)
	}

	req, err := http.NewRequest(method, url, bodyReader)
	if err != nil {
		return nil, err
	}
	hdr, err := c.headers(agent)
	if err != nil {
		return nil, err
	}
	req.Header = hdr
	if jsonBody != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	ok := false
	for _, code := range okStatuses {
		if resp.StatusCode == code {
			ok = true
			break
		}
	}
	if !ok {
		body := string(raw)
		if len(body) > 500 {
			body = body[:500]
		}
		return nil, fmt.Errorf(texts.MsgErrHTTP, resp.StatusCode, body)
	}
	if len(raw) == 0 {
		return nil, nil
	}
	return json.RawMessage(raw), nil
}

func (c *AgentClient) Start_Pairing() (*model.PairingStartOut, error) {
	raw, err := c.request_JSON(http.MethodPost, PathPairingStart, nil, false)
	if err != nil {
		return nil, err
	}
	var out model.PairingStartOut
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

func (c *AgentClient) Try_Complete_Pairing(pairingID string) (*model.PairingCompleteOut, error) {
	url := c.BaseURL + fmt.Sprintf(PathPairingComplete, pairingID)
	c.debug_Log(fmt.Sprintf(texts.MsgDebugRequest, http.MethodPost, url))

	req, err := http.NewRequest(http.MethodPost, url, nil)
	if err != nil {
		return nil, err
	}
	hdr, err := c.headers(false)
	if err != nil {
		return nil, err
	}
	req.Header = hdr

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode == 200 {
		var out model.PairingCompleteOut
		if err := json.Unmarshal(raw, &out); err != nil {
			return nil, err
		}
		return &out, nil
	}
	if resp.StatusCode == 409 {
		return nil, nil
	}
	body := string(raw)
	if len(body) > 500 {
		body = body[:500]
	}
	return nil, fmt.Errorf(texts.MsgErrHTTP, resp.StatusCode, body)
}

func (c *AgentClient) Get_Config() (*model.ConfigOut, error) {
	raw, err := c.request_JSON(http.MethodGet, PathAgentConfig, nil, true)
	if err != nil {
		return nil, err
	}
	var out model.ConfigOut
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

func (c *AgentClient) Next_HeartbeatPath(paths []string) string {
	usable := make([]string, 0, len(paths))
	for _, path := range paths {
		path = strings.TrimSpace(path)
		if path == "" || path == "/api/telemetry/batch" {
			continue
		}
		usable = append(usable, path)
	}
	if len(usable) == 0 {
		usable = []string{"/v1/metrics", "/cdn/edge-check"}
	}
	path := usable[c.pathCursor%len(usable)]
	c.pathCursor++
	return path
}

func (c *AgentClient) Post_Heartbeat(path string, agentVersion string, statusPayload map[string]any) (*model.HeartbeatOut, error) {
	if path == "" {
		path = PathAgentHeartbeat
	}
	body := map[string]any{
		"agent_version":  agentVersion,
		"status_payload": statusPayload,
	}
	raw, err := c.request_JSON(http.MethodPost, path, body, true)
	if err != nil {
		return nil, err
	}
	return parse_Heartbeat(raw)
}

func parse_Heartbeat(raw json.RawMessage) (*model.HeartbeatOut, error) {
	var direct model.HeartbeatOut
	if err := json.Unmarshal(raw, &direct); err != nil {
		return nil, err
	}
	if direct.Ok || direct.ConfigVersion != nil {
		return &direct, nil
	}
	var wrapped struct {
		Result *model.HeartbeatOut `json:"result"`
	}
	if json.Unmarshal(raw, &wrapped) == nil && wrapped.Result != nil {
		return wrapped.Result, nil
	}
	return &direct, nil
}

func (c *AgentClient) Post_Events(events []model.AgentEvent) (*model.EventsOut, error) {
	body := map[string]any{"events": events}
	raw, err := c.request_JSON(http.MethodPost, PathAgentEvents, body, true)
	if err != nil {
		return nil, err
	}
	var out model.EventsOut
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

func (c *AgentClient) Claim_Commands() (*model.ClaimOut, error) {
	raw, err := c.request_JSON(http.MethodPost, PathAgentCommandsClaim, nil, true)
	if err != nil {
		return nil, err
	}
	var out model.ClaimOut
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

func (c *AgentClient) Get_FsPackBytes(token string) ([]byte, error) {
	path := fmt.Sprintf(PathAgentFsPack, token)
	url := c.BaseURL + path
	c.debug_Log(fmt.Sprintf(texts.MsgDebugRequest, http.MethodGet, url))

	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	hdr, err := c.headers(true)
	if err != nil {
		return nil, err
	}
	req.Header = hdr
	req.Header.Set("Accept", "application/octet-stream")

	// Архив до 32 MiB - даём запас по таймауту
	client := c.HTTPClient
	if client == nil {
		client = &http.Client{Timeout: 120 * time.Second}
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != 200 {
		body := string(raw)
		if len(body) > 500 {
			body = body[:500]
		}
		return nil, fmt.Errorf(texts.MsgErrHTTP, resp.StatusCode, body)
	}
	return raw, nil
}

func (c *AgentClient) Get_Cover(pathOrURL string) {
	target := pathOrURL
	if strings.HasPrefix(pathOrURL, "/") {
		target = c.BaseURL + pathOrURL
	}
	c.debug_Log(fmt.Sprintf(texts.MsgDebugRequest, http.MethodGet, target))
	req, err := http.NewRequest(http.MethodGet, target, nil)
	if err != nil {
		return
	}
	if c.UserAgent != "" {
		req.Header.Set("User-Agent", c.UserAgent)
	}
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return
	}
	_ = resp.Body.Close()
}
