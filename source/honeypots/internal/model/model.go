package model

import "encoding/json"

type BannerModule struct {
	Enabled *bool  `json:"enabled"`
	Version string `json:"version"`
}

func (m BannerModule) IsEnabled() bool {
	return m.Enabled == nil || *m.Enabled
}

type AuthModule struct {
	Enabled        *bool    `json:"enabled"`
	Mode           string   `json:"mode"`
	CredentialIDs  []string `json:"credential_ids"`
	DelayMsMin     int      `json:"delay_ms_min"`
	DelayMsMax     int      `json:"delay_ms_max"`
	StickyTTLHours int      `json:"sticky_ttl_hours"`
	Path           string   `json:"path"`
	Realm          string   `json:"realm"`
}

func (m AuthModule) IsEnabled(defaultValue bool) bool {
	if m.Enabled == nil {
		return defaultValue
	}
	return *m.Enabled
}

type ShellModule struct {
	Enabled       *bool  `json:"enabled"`
	FsPack        string `json:"fs_pack"`
	MaxSessionSec int    `json:"max_session_sec"`
}

func (m ShellModule) IsEnabled() bool {
	return m.Enabled == nil || *m.Enabled
}

type SshModules struct {
	Banner BannerModule `json:"banner"`
	Auth   AuthModule   `json:"auth"`
	Shell  ShellModule  `json:"shell"`
}

type HttpPersonalityModule struct {
	Enabled *bool             `json:"enabled"`
	Server  string            `json:"server"`
	Title   string            `json:"title"`
	Headers map[string]string `json:"headers"`
}

func (m HttpPersonalityModule) IsEnabled() bool {
	return m.Enabled == nil || *m.Enabled
}

type HttpRoute struct {
	Path        string   `json:"path"`
	Methods     []string `json:"methods"`
	Status      int      `json:"status"`
	ContentType string   `json:"content_type"`
	Body        string   `json:"body"`
}

type HttpRoutesModule struct {
	Routes        []HttpRoute `json:"routes"`
	DefaultStatus int         `json:"default_status"`
	DefaultBody   string      `json:"default_body"`
}

type HttpModules struct {
	Personality HttpPersonalityModule `json:"personality"`
	Auth        AuthModule            `json:"auth"`
	Routes      HttpRoutesModule      `json:"routes"`
}

type TcpBannerModules struct {
	Banner string `json:"banner"`
}

type DbBannerModule struct {
	Enabled *bool  `json:"enabled"`
	Version string `json:"version"`
}

type SessionModule struct {
	Enabled       *bool `json:"enabled"`
	MaxSessionSec int   `json:"max_session_sec"`
}

func (m SessionModule) IsEnabled() bool {
	return m.Enabled == nil || *m.Enabled
}

func (m SessionModule) MaxSec() int {
	if m.MaxSessionSec <= 0 {
		return 120
	}
	return m.MaxSessionSec
}

type DbModules struct {
	Banner  DbBannerModule `json:"banner"`
	Auth    AuthModule     `json:"auth"`
	Session SessionModule  `json:"session"`
}

type ServiceBlock struct {
	Type         string           `json:"type"`
	ID           string           `json:"id"`
	Port         int              `json:"port"`
	Enabled      *bool            `json:"enabled"`
	SshModules   SshModules       `json:"-"`
	HttpModules  HttpModules      `json:"-"`
	TcpModules   TcpBannerModules `json:"-"`
	PgModules    DbModules        `json:"-"`
	RedisModules DbModules        `json:"-"`
	MysqlModules DbModules        `json:"-"`
}

func (s ServiceBlock) IsEnabled() bool {
	if s.Enabled == nil {
		return true
	}
	return *s.Enabled
}

func (s *ServiceBlock) UnmarshalJSON(data []byte) error {
	type serviceWire struct {
		Type    string          `json:"type"`
		ID      string          `json:"id"`
		Port    int             `json:"port"`
		Enabled *bool           `json:"enabled"`
		Modules json.RawMessage `json:"modules"`
	}
	var wire serviceWire
	if err := json.Unmarshal(data, &wire); err != nil {
		return err
	}
	s.Type = wire.Type
	s.ID = wire.ID
	s.Port = wire.Port
	s.Enabled = wire.Enabled
	if len(wire.Modules) == 0 || string(wire.Modules) == "null" {
		return nil
	}
	switch wire.Type {
	case "ssh":
		return json.Unmarshal(wire.Modules, &s.SshModules)
	case "http":
		return json.Unmarshal(wire.Modules, &s.HttpModules)
	case "tcp_banner":
		return json.Unmarshal(wire.Modules, &s.TcpModules)
	case "postgres":
		return json.Unmarshal(wire.Modules, &s.PgModules)
	case "redis":
		return json.Unmarshal(wire.Modules, &s.RedisModules)
	case "mysql":
		return json.Unmarshal(wire.Modules, &s.MysqlModules)
	}
	return nil
}

type CredentialBlock struct {
	ID       string `json:"id"`
	Username string `json:"username"`
	Password string `json:"password"`
	Note     string `json:"note"`
}

type LoggingBlock struct {
	CaptureCredentials *bool `json:"capture_credentials"`
	CapturePayloads    *bool `json:"capture_payloads"`
	CaptureSourceMeta  *bool `json:"capture_source_meta"`
}

func (l LoggingBlock) Keeps_Credentials() bool {
	return l.CaptureCredentials == nil || *l.CaptureCredentials
}

func (l LoggingBlock) Keeps_Payloads() bool {
	return l.CapturePayloads == nil || *l.CapturePayloads
}

func (l LoggingBlock) Keeps_SourceMeta() bool {
	return l.CaptureSourceMeta == nil || *l.CaptureSourceMeta
}

type JitterMethod struct {
	Enabled           *bool `json:"enabled"`
	BeaconIntervalSec int   `json:"beacon_interval_sec"`
	JitterPct         int   `json:"jitter_pct"`
}

func (m JitterMethod) IsEnabled() bool {
	return m.Enabled == nil || *m.Enabled
}

type CoverMethod struct {
	Enabled *bool    `json:"enabled"`
	URLs    []string `json:"urls"`
}

func (m CoverMethod) IsEnabled() bool {
	return m.Enabled == nil || *m.Enabled
}

type PathRotationMethod struct {
	Enabled *bool    `json:"enabled"`
	Paths   []string `json:"paths"`
}

func (m PathRotationMethod) IsEnabled() bool {
	return m.Enabled == nil || *m.Enabled
}

type MimicryMethod struct {
	Enabled               *bool  `json:"enabled"`
	UserAgent             string `json:"user_agent"`
	TLSFingerprintProfile string `json:"tls_fingerprint_profile"`
}

func (m MimicryMethod) IsEnabled() bool {
	return m.Enabled == nil || *m.Enabled
}

type ProcessMaskMethod struct {
	Enabled *bool  `json:"enabled"`
	Name    string `json:"name"`
}

func (m ProcessMaskMethod) IsEnabled() bool {
	return m.Enabled == nil || *m.Enabled
}

type CourierMethod struct {
	Enabled            *bool `json:"enabled"`
	CollectIntervalSec int   `json:"collect_interval_sec"`
}

func (m CourierMethod) IsEnabled() bool {
	return m.Enabled != nil && *m.Enabled
}

type MaskBlock struct {
	CollectionMode     string             `json:"collection_mode"`
	Courier            CourierMethod      `json:"courier"`
	Jitter             JitterMethod       `json:"jitter"`
	Cover              CoverMethod        `json:"cover"`
	PathRotation       PathRotationMethod `json:"path_rotation"`
	Mimicry            MimicryMethod      `json:"mimicry"`
	ProcessMask        ProcessMaskMethod  `json:"process_mask"`
	DecoyContentSeed   string             `json:"decoy_content_seed"`
	ServicePersonality string             `json:"service_personality"`
}

func (m MaskBlock) IsCourierMode() bool {
	if m.Courier.IsEnabled() {
		return true
	}
	return m.CollectionMode == "courier"
}

func (m *MaskBlock) UnmarshalJSON(data []byte) error {
	if string(data) == "null" {
		return nil
	}
	var raw map[string]json.RawMessage
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}
	_, hasJitter := raw["jitter"]
	_, hasCover := raw["cover"]
	_, hasPaths := raw["path_rotation"]
	_, hasMimicry := raw["mimicry"]
	_, hasProcess := raw["process_mask"]
	_, hasCourier := raw["courier"]
	nested := hasJitter || hasCover || hasPaths || hasMimicry || hasProcess || hasCourier
	if !nested && has_FlatMask(raw) {
		return m.unmarshal_Flat(raw)
	}
	type nestedMask MaskBlock
	return json.Unmarshal(data, (*nestedMask)(m))
}

func has_FlatMask(raw map[string]json.RawMessage) bool {
	for _, key := range []string{
		"beacon_interval_sec", "jitter_pct", "cover_urls",
		"collector_path_set", "user_agent", "process_name",
	} {
		if _, ok := raw[key]; ok {
			return true
		}
	}
	return false
}

func (m *MaskBlock) unmarshal_Flat(raw map[string]json.RawMessage) error {
	var flat struct {
		BeaconIntervalSec  int      `json:"beacon_interval_sec"`
		JitterPct          int      `json:"jitter_pct"`
		CollectorPathSet   []string `json:"collector_path_set"`
		UserAgent          string   `json:"user_agent"`
		CoverUrls          []string `json:"cover_urls"`
		ProcessName        string   `json:"process_name"`
		DecoyContentSeed   string   `json:"decoy_content_seed"`
		ServicePersonality string   `json:"service_personality"`
		TLSProfile         string   `json:"tls_fingerprint_profile"`
	}
	encoded, err := json.Marshal(raw)
	if err != nil {
		return err
	}
	if err := json.Unmarshal(encoded, &flat); err != nil {
		return err
	}
	on := true
	m.Jitter = JitterMethod{
		Enabled:           boolPtr(on),
		BeaconIntervalSec: flat.BeaconIntervalSec,
		JitterPct:         flat.JitterPct,
	}
	coverOn := true
	if _, ok := raw["cover_urls"]; ok && len(flat.CoverUrls) == 0 {
		coverOn = false
	}
	m.Cover = CoverMethod{Enabled: boolPtr(coverOn), URLs: flat.CoverUrls}
	pathsOn := true
	if _, ok := raw["collector_path_set"]; ok && len(flat.CollectorPathSet) == 0 {
		pathsOn = false
	}
	m.PathRotation = PathRotationMethod{Enabled: boolPtr(pathsOn), Paths: flat.CollectorPathSet}
	m.Mimicry = MimicryMethod{
		Enabled:               boolPtr(true),
		UserAgent:             flat.UserAgent,
		TLSFingerprintProfile: flat.TLSProfile,
	}
	processOn := true
	if _, ok := raw["process_name"]; ok && flat.ProcessName == "" {
		processOn = false
	}
	m.ProcessMask = ProcessMaskMethod{Enabled: boolPtr(processOn), Name: flat.ProcessName}
	m.DecoyContentSeed = flat.DecoyContentSeed
	m.ServicePersonality = flat.ServicePersonality
	return nil
}

func boolPtr(value bool) *bool {
	return &value
}

// BaitBlock - подсказка на соседний сервис мини-парка (файл FS или HTTP route).
type BaitBlock struct {
	Kind      string `json:"kind"` // file | http_route
	Path      string `json:"path"`
	Body      string `json:"body"`
	ServiceID string `json:"service_id"`
}

// HoneytokenBlock - canary; hit → honeytoken_hit.
type HoneytokenBlock struct {
	ID        string `json:"id"`
	Kind      string `json:"kind"` // file | url | key | credential
	Path      string `json:"path"`
	Body      string `json:"body"`
	ServiceID string `json:"service_id"`
	Username  string `json:"username"`
	Password  string `json:"password"`
}

// EmulationExpose - NAT port-forward host→guest.
type EmulationExpose struct {
	HostPort  int    `json:"host_port"`
	GuestPort int    `json:"guest_port"`
	Proto     string `json:"proto"`
}

// EmulationBlock - High: VirtualBox VM на хосте-ловушке.
type EmulationBlock struct {
	Enabled    bool              `json:"enabled"`
	Runtime    string            `json:"runtime"`
	ImageToken string            `json:"image_token"`
	VmName     string            `json:"vm_name"`
	Cpus       int               `json:"cpus"`
	MemoryMb   int               `json:"memory_mb"`
	Snapshot   string            `json:"snapshot"`
	Expose     []EmulationExpose `json:"expose"`
	AutoStart  bool              `json:"auto_start"`
}

type ProfileBlocks struct {
	Services    []ServiceBlock    `json:"services"`
	Credentials []CredentialBlock `json:"credentials"`
	Baits       []BaitBlock       `json:"baits"`
	Honeytokens []HoneytokenBlock `json:"honeytokens"`
	Emulation   EmulationBlock    `json:"emulation"`
	Logging     LoggingBlock      `json:"logging"`
	Mask        MaskBlock         `json:"mask"`
}

type Profile struct {
	ID               string        `json:"id"`
	Name             string        `json:"name"`
	Description      string        `json:"description"`
	InteractionLevel string        `json:"interaction_level"`
	Blocks           ProfileBlocks `json:"blocks"`
	ConfigVersion    int           `json:"config_version"`
	ConfigHash       string        `json:"config_hash"`
}

func (p Profile) CredentialsFor(ids []string) []CredentialBlock {
	if len(ids) == 0 {
		return nil
	}
	selected := make(map[string]bool, len(ids))
	for _, id := range ids {
		selected[id] = true
	}
	out := make([]CredentialBlock, 0, len(ids))
	for _, credential := range p.Blocks.Credentials {
		if selected[credential.ID] {
			out = append(out, credential)
		}
	}
	return out
}

func (p Profile) MaskValue_Int(key string, defaultVal int) int {
	jitter := p.Blocks.Mask.Jitter
	switch key {
	case "beacon_interval_sec":
		if jitter.BeaconIntervalSec > 0 {
			return jitter.BeaconIntervalSec
		}
	case "jitter_pct":
		if !jitter.IsEnabled() {
			return 0
		}
		if jitter.JitterPct > 0 || jitter.BeaconIntervalSec > 0 {
			return jitter.JitterPct
		}
	}
	return defaultVal
}

type AgentEvent struct {
	EventType  string         `json:"event_type"`
	SourceIP   *string        `json:"source_ip"`
	SourcePort *int           `json:"source_port"`
	OccurredAt string         `json:"occurred_at"`
	Payload    map[string]any `json:"payload"`
}

type ConfigOut struct {
	TrapID  string   `json:"trap_id"`
	Profile *Profile `json:"profile"`
}

type HeartbeatOut struct {
	Ok            bool `json:"ok"`
	ConfigVersion any  `json:"config_version"`
}

type EventsOut struct {
	Accepted int `json:"accepted"`
}

type PairingStartOut struct {
	PairingID  string `json:"pairing_id"`
	DeviceCode string `json:"device_code"`
	ExpiresAt  string `json:"expires_at"`
}

type PairingCompleteOut struct {
	TrapID     string `json:"trap_id"`
	AgentToken string `json:"agent_token"`
	Status     string `json:"status"`
}

type ClaimOut struct {
	Command *struct {
		ID          string         `json:"id"`
		CommandType string         `json:"command_type"`
		Payload     map[string]any `json:"payload"`
	} `json:"command"`
}

func PtrString(v string) *string { return &v }
func PtrInt(v int) *int          { return &v }
