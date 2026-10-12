package auth

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"

	"honeyforge/honeypots/internal/model"
)

const (
	ModeAllowAll            = "allow_all"
	ModeAllowListed         = "allow_listed"
	ModeSecondAttemptSticky = "second_attempt_sticky"
)

type Binding struct {
	Username  string    `json:"username"`
	Password  string    `json:"password"`
	Accepted  bool      `json:"accepted"`
	Attempts  int       `json:"attempts"`
	ExpiresAt time.Time `json:"expires_at"`
}

type diskState struct {
	Bindings map[string]Binding `json:"bindings"`
}

type Store struct {
	path     string
	mu       sync.Mutex
	bindings map[string]Binding
}

func New_Store(path string) *Store {
	store := &Store{
		path:     path,
		bindings: map[string]Binding{},
	}
	store.load()
	return store
}

func (s *Store) load() {
	raw, err := os.ReadFile(s.path)
	if err != nil {
		return
	}
	var state diskState
	if json.Unmarshal(raw, &state) != nil || state.Bindings == nil {
		return
	}
	s.bindings = state.Bindings
	// Старый файл хранил первую попытку без счётчика. Считаем её уже совершённой.
	for key, binding := range s.bindings {
		if binding.Accepted || binding.Attempts > 0 {
			continue
		}
		if binding.Username == "" && binding.Password == "" {
			continue
		}
		binding.Attempts = 1
		s.bindings[key] = binding
	}
}

func (s *Store) save() {
	state := diskState{Bindings: s.bindings}
	raw, err := json.MarshalIndent(state, "", "\t")
	if err != nil {
		return
	}
	if err := os.MkdirAll(filepath.Dir(s.path), 0o755); err != nil {
		return
	}
	tempPath := s.path + ".tmp"
	if os.WriteFile(tempPath, raw, 0o600) == nil {
		_ = os.Rename(tempPath, s.path)
	}
}

func credentials_Match(
	username string,
	password string,
	credentials []model.CredentialBlock,
) bool {
	for _, credential := range credentials {
		if credential.Username == username && credential.Password == password {
			return true
		}
	}
	return false
}

func authFilter_Allows(
	module model.AuthModule,
	username string,
	password string,
	credentials []model.CredentialBlock,
) bool {
	// Пустой credential_ids значит «любая пара». Иначе только пары из пула.
	if len(module.CredentialIDs) == 0 {
		return true
	}
	return credentials_Match(username, password, credentials)
}

// Evaluate применяет режим авторизации. Sticky-привязка сохраняется между рестартами.
func (s *Store) Evaluate(
	serviceID string,
	sourceIP string,
	username string,
	password string,
	module model.AuthModule,
	credentials []model.CredentialBlock,
) bool {
	switch module.Mode {
	case "", ModeAllowAll:
		return true
	case ModeAllowListed:
		return credentials_Match(username, password, credentials)
	case ModeSecondAttemptSticky:
		if !authFilter_Allows(module, username, password, credentials) {
			return false
		}
		return s.evaluate_Sticky(
			serviceID,
			sourceIP,
			username,
			password,
			module.StickyTTLHours,
		)
	default:
		return false
	}
}

func (s *Store) evaluate_Sticky(
	serviceID string,
	sourceIP string,
	username string,
	password string,
	ttlHours int,
) bool {
	s.mu.Lock()
	defer s.mu.Unlock()

	if ttlHours <= 0 {
		ttlHours = 72
	}
	now := time.Now().UTC()
	key := serviceID + "|" + sourceIP
	binding, exists := s.bindings[key]
	if exists && !binding.ExpiresAt.IsZero() && now.After(binding.ExpiresAt) {
		delete(s.bindings, key)
		exists = false
	}
	ttl := time.Duration(ttlHours) * time.Hour
	// Уже пустили: дальше только та пара, которой открыли сессию.
	if exists && binding.Accepted {
		if binding.Username == username && binding.Password == password {
			binding.ExpiresAt = now.Add(ttl)
			s.bindings[key] = binding
			s.save()
			return true
		}
		return false
	}
	// Первая подходящая попытка с этого IP отклоняется.
	// Со второй попытки пускаем и запоминаем именно эту пару, даже если она другая.
	attempts := 1
	if exists {
		attempts = binding.Attempts + 1
	}
	accepted := attempts >= 2
	s.bindings[key] = Binding{
		Username:  username,
		Password:  password,
		Accepted:  accepted,
		Attempts:  attempts,
		ExpiresAt: now.Add(ttl),
	}
	s.save()
	return accepted
}
