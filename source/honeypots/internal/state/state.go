package state

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"metricsd/internal/texts"
)

type AgentState struct {
	TrapID     string `json:"trap_id"`
	AgentToken string `json:"agent_token"`
	SavedAt    string `json:"saved_at"`
}

func Now_Iso() string {
	return time.Now().UTC().Format(time.RFC3339Nano)
}

func Has_Token(path string) bool {
	data, err := os.ReadFile(path)
	if err != nil {
		return false
	}
	var st AgentState
	if err := json.Unmarshal(data, &st); err != nil {
		return false
	}
	return st.AgentToken != ""
}

func Save_State(path, trapID, agentToken string) error {
	payload := AgentState{
		TrapID:     trapID,
		AgentToken: agentToken,
		SavedAt:    Now_Iso(),
	}
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	if err := os.WriteFile(path, raw, 0o600); err != nil {
		return err
	}
	fmt.Printf(texts.MsgTokenSaved+"\n", path)
	return nil
}

func Load_Token(path string) (string, string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", "", err
	}
	var st AgentState
	if err := json.Unmarshal(data, &st); err != nil {
		return "", "", err
	}
	if st.AgentToken == "" {
		return "", "", fmt.Errorf(texts.MsgErrNoAgentToken, path)
	}
	trapID := st.TrapID
	if trapID == "" {
		trapID = "?"
	}
	fmt.Printf(texts.MsgTokenLoaded+"\n", path, trapID)
	return st.AgentToken, trapID, nil
}
