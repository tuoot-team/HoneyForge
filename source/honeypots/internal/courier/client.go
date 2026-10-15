package courier

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"metricsd/internal/texts"
	"metricsd/internal/tlsutil"
)

const (
	CourierHeader = "X-Courier-Token"

	PathPairingStart    = "/api/v1/courier-pairing/start"
	PathPairingComplete = "/api/v1/courier-pairing/%s/complete"
	PathConfig          = "/api/v1/courier/config"
	PathVisitClaim      = "/api/v1/courier/visits/claim"
	PathVisitComplete   = "/api/v1/courier/visits/%s/complete"
)

type Client struct {
	BaseURL      string
	CourierToken string
	Debug        bool
	HTTPClient   *http.Client
}

func New_Client(baseURL string, debug bool) (*Client, error) {
	httpClient, err := tlsutil.New_HTTPClient(60 * time.Second)
	if err != nil {
		return nil, err
	}
	return &Client{
		BaseURL:    strings.TrimRight(baseURL, "/"),
		Debug:      debug,
		HTTPClient: httpClient,
	}, nil
}

func (c *Client) debug_Log(message string) {
	if c.Debug {
		println("[DEBUG]", message)
	}
}

func (c *Client) request_JSON(
	method, path string,
	jsonBody any,
	withToken bool,
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
	req.Header.Set("Accept", "application/json")
	if jsonBody != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if withToken {
		if c.CourierToken == "" {
			return nil, fmt.Errorf("%s", texts.MsgErrNoTokenClient)
		}
		req.Header.Set(CourierHeader, c.CourierToken)
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
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(raw))
	}
	return raw, nil
}

type PairingStartOut struct {
	PairingID  string `json:"pairing_id"`
	DeviceCode string `json:"device_code"`
	ExpiresAt  string `json:"expires_at"`
}

type PairingCompleteOut struct {
	CourierID    string `json:"courier_id"`
	CourierToken string `json:"courier_token"`
}

type VisitClaimOut struct {
	VisitID    *string        `json:"visit_id"`
	TrapID     *string        `json:"trap_id"`
	SSH        map[string]any `json:"ssh"`
	BufferPath *string        `json:"buffer_path"`
	WipeHints  []string       `json:"wipe_hints"`
}

type VisitEventIn struct {
	EventType     string         `json:"event_type"`
	SourceIP      *string        `json:"source_ip,omitempty"`
	SourcePort    *int           `json:"source_port,omitempty"`
	OccurredAt    *string        `json:"occurred_at,omitempty"`
	Payload       map[string]any `json:"payload"`
	AgentBufferID *int64         `json:"agent_buffer_id,omitempty"`
}

type VisitCompleteIn struct {
	OK     bool           `json:"ok"`
	Error  *string        `json:"error,omitempty"`
	Events []VisitEventIn `json:"events"`
}

type VisitCompleteOut struct {
	OK       bool   `json:"ok"`
	Accepted int    `json:"accepted"`
	Status   string `json:"status"`
}

func (c *Client) Start_Pairing() (*PairingStartOut, error) {
	raw, err := c.request_JSON("POST", PathPairingStart, map[string]any{}, false)
	if err != nil {
		return nil, err
	}
	var out PairingStartOut
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

func (c *Client) Try_Complete_Pairing(pairingID string) (*PairingCompleteOut, error) {
	path := fmt.Sprintf(PathPairingComplete, pairingID)
	url := c.BaseURL + path
	c.debug_Log(fmt.Sprintf(texts.MsgDebugRequest, "POST", url))
	req, err := http.NewRequest("POST", url, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Accept", "application/json")
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode == 200 || resp.StatusCode == 201 {
		var out PairingCompleteOut
		if err := json.Unmarshal(raw, &out); err != nil {
			return nil, err
		}
		return &out, nil
	}
	if resp.StatusCode == 409 {
		return nil, nil
	}
	return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(raw))
}

func (c *Client) Get_Config() error {
	_, err := c.request_JSON("GET", PathConfig, nil, true)
	return err
}

func (c *Client) Claim_Visit() (*VisitClaimOut, error) {
	raw, err := c.request_JSON("POST", PathVisitClaim, map[string]any{}, true)
	if err != nil {
		return nil, err
	}
	var out VisitClaimOut
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

func (c *Client) Complete_Visit(visitID string, body VisitCompleteIn) (*VisitCompleteOut, error) {
	path := fmt.Sprintf(PathVisitComplete, visitID)
	raw, err := c.request_JSON("POST", path, body, true)
	if err != nil {
		return nil, err
	}
	var out VisitCompleteOut
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	return &out, nil
}
