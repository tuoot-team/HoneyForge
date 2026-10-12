package buffer

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"honeyforge/honeypots/internal/model"
	"honeyforge/honeypots/internal/texts"
)

type storedEvent struct {
	ID      int64            `json:"id"`
	Payload model.AgentEvent `json:"payload"`
	Sent    bool             `json:"sent"`
}

type fileStore struct {
	NextID int64         `json:"next_id"`
	Events []storedEvent `json:"events"`
}

type EventBuffer struct {
	path  string
	debug bool
	mu    sync.Mutex
}

func New_EventBuffer(path string, debug bool) (*EventBuffer, error) {
	b := &EventBuffer{path: path, debug: debug}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, err
	}
	if _, err := os.Stat(path); os.IsNotExist(err) {
		if err := b.save(&fileStore{NextID: 1}); err != nil {
			return nil, err
		}
	}
	return b, nil
}

func (b *EventBuffer) Close() error { return nil }

func (b *EventBuffer) debug_Log(message string) {
	if b.debug {
		println("[DEBUG]", message)
	}
}

func (b *EventBuffer) load() (*fileStore, error) {
	data, err := os.ReadFile(b.path)
	if err != nil {
		return nil, err
	}
	var st fileStore
	if len(data) == 0 {
		return &fileStore{NextID: 1}, nil
	}
	if err := json.Unmarshal(data, &st); err != nil {
		return nil, err
	}
	if st.NextID < 1 {
		st.NextID = 1
	}
	return &st, nil
}

func (b *EventBuffer) save(st *fileStore) error {
	raw, err := json.MarshalIndent(st, "", "  ")
	if err != nil {
		return err
	}
	tmp := b.path + ".tmp"
	if err := os.WriteFile(tmp, raw, 0o600); err != nil {
		return err
	}
	return os.Rename(tmp, b.path)
}

func (b *EventBuffer) Add(event model.AgentEvent) error {
	b.mu.Lock()
	defer b.mu.Unlock()
	st, err := b.load()
	if err != nil {
		return err
	}
	st.Events = append(st.Events, storedEvent{
		ID:      st.NextID,
		Payload: event,
		Sent:    false,
	})
	st.NextID++
	if err := b.save(st); err != nil {
		return err
	}
	b.debug_Log(fmt.Sprintf(texts.MsgBufferAdded, event.EventType))
	return nil
}

type PendingRow struct {
	ID    int64
	Event model.AgentEvent
}

func (b *EventBuffer) Pending(limit int) ([]PendingRow, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	st, err := b.load()
	if err != nil {
		return nil, err
	}
	var out []PendingRow
	for _, ev := range st.Events {
		if ev.Sent {
			continue
		}
		out = append(out, PendingRow{ID: ev.ID, Event: ev.Payload})
		if len(out) >= limit {
			break
		}
	}
	return out, nil
}

func (b *EventBuffer) Mark_Sent(ids []int64) error {
	if len(ids) == 0 {
		return nil
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	st, err := b.load()
	if err != nil {
		return err
	}
	want := map[int64]bool{}
	for _, id := range ids {
		want[id] = true
	}
	for i := range st.Events {
		if want[st.Events[i].ID] {
			st.Events[i].Sent = true
		}
	}
	if err := b.save(st); err != nil {
		return err
	}
	b.debug_Log(fmt.Sprintf(texts.MsgBufferSent, len(ids)))
	return nil
}

func (b *EventBuffer) Count_Pending() (int, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	st, err := b.load()
	if err != nil {
		return 0, err
	}
	n := 0
	for _, ev := range st.Events {
		if !ev.Sent {
			n++
		}
	}
	return n, nil
}
