package mid

import (
	"testing"

	"metricsd/internal/model"
)

func Test_Expand_Honeytokens(t *testing.T) {
	on := true
	profile := model.Profile{
		Blocks: model.ProfileBlocks{
			Services: []model.ServiceBlock{
				{Type: "http", ID: "http-main", Port: 8080, Enabled: &on},
			},
			Honeytokens: []model.HoneytokenBlock{
				{ID: "notes-canary", Kind: "file", Path: "/home/{{user}}/NOTES.txt"},
				{ID: "internal-url", Kind: "url", ServiceID: "http-main", Path: "/internal"},
				{
					ID:       "aws-key",
					Kind:     "key",
					Path:     "/opt/app/secrets.env",
					Body:     "AWS_ACCESS_KEY_ID=AKIA\n",
				},
				{
					ID:       "backup-cred",
					Kind:     "credential",
					Username: "backup",
					Password: "CanaryBackup1!",
					Path:     "/home/{{user}}/.aws/credentials",
					Body:     "[default]\nkey=1\n",
				},
			},
		},
	}
	reg := Expand_Honeytokens(profile, "ops")
	if _, ok := reg.Files["/home/ops/NOTES.txt"]; !ok {
		t.Fatalf("file token missing: %#v", reg.Files)
	}
	if _, ok := reg.HTTP[http_TokenKey("http-main", "/internal")]; !ok {
		t.Fatalf("url token missing: %#v", reg.HTTP)
	}
	if body := reg.PlantFiles["/opt/app/secrets.env"]; body == "" {
		t.Fatalf("key plant missing")
	}
	if _, ok := reg.Creds[cred_TokenKey("backup", "CanaryBackup1!")]; !ok {
		t.Fatalf("cred token missing")
	}
	if _, ok := reg.Files["/home/ops/.aws/credentials"]; !ok {
		t.Fatalf("cred file token missing")
	}
}

func Test_Emit_HoneytokenHit_OnRead(t *testing.T) {
	var got []model.AgentEvent
	shell := New_FakeShell("ops", "host", "ubuntu-22.04", nil, nil, 22, func(ev model.AgentEvent) {
		got = append(got, ev)
	}, nil)
	shell.Tree["/home/ops/NOTES.txt"] = "secret notes\n"
	shell.TokenFiles = map[string]HoneytokenMeta{
		"/home/ops/NOTES.txt": {ID: "notes-canary", Kind: "file"},
	}
	out := shell.cmd_Cat([]string{"NOTES.txt"})
	if out != "secret notes\n" {
		t.Fatalf("cat body: %q", out)
	}
	found := false
	for _, ev := range got {
		if ev.EventType != "honeytoken_hit" {
			continue
		}
		found = true
		if ev.Payload["token_id"] != "notes-canary" {
			t.Fatalf("payload: %#v", ev.Payload)
		}
		if ev.Payload["trigger"] != "read" {
			t.Fatalf("trigger: %#v", ev.Payload)
		}
	}
	if !found {
		t.Fatalf("honeytoken_hit not emitted: %#v", got)
	}
}

func Test_Match_HTTP_And_Cred(t *testing.T) {
	reg := &HoneytokenRegistry{
		HTTP: map[string]HoneytokenMeta{
			http_TokenKey("http-main", "/internal"): {ID: "internal-url", Kind: "url"},
		},
		Creds: map[string]HoneytokenMeta{
			cred_TokenKey("backup", "CanaryBackup1!"): {ID: "backup-cred", Kind: "credential"},
		},
	}
	meta, ok := reg.Match_HTTP("http-main", "/internal")
	if !ok || meta.ID != "internal-url" {
		t.Fatalf("http match: %v %#v", ok, meta)
	}
	meta, ok = reg.Match_Cred("backup", "CanaryBackup1!")
	if !ok || meta.ID != "backup-cred" {
		t.Fatalf("cred match: %v %#v", ok, meta)
	}
}
