package mid

import "testing"

func TestCheck_Image(t *testing.T) {
	ok, err := Check_Image("  ghcr.io/org/honeypot:1.2.3  ")
	if err != nil || ok != "ghcr.io/org/honeypot:1.2.3" {
		t.Fatalf("good image: %q %v", ok, err)
	}
	for _, bad := range []string{"", "has space", "../etc", "-privileged", "img;rm"} {
		if _, err := Check_Image(bad); err == nil {
			t.Fatalf("accepted bad image %q", bad)
		}
	}
}

func TestContainer_Name(t *testing.T) {
	if got := Container_Name("cowrie"); got != "hf-cowrie" {
		t.Fatalf("name: %s", got)
	}
	if got := Container_Name("a/b"); got != "hf-a-b" {
		t.Fatalf("slash: %s", got)
	}
	if got := Container_Name(""); got != "hf-container" {
		t.Fatalf("empty: %s", got)
	}
}

func TestParse_ContainerLine(t *testing.T) {
	ev, ok := Parse_ContainerLine(
		`{"event_type":"port_connect","source_ip":"1.2.3.4","source_port":54321,"payload":{}}`,
		"cowrie",
		2222,
	)
	if !ok || ev.EventType != "port_connect" || ev.SourceIP == nil || *ev.SourceIP != "1.2.3.4" {
		t.Fatalf("event: %+v ok=%v", ev, ok)
	}
	if ev.SourcePort == nil || *ev.SourcePort != 54321 {
		t.Fatalf("port: %+v", ev.SourcePort)
	}
	if ev.Payload["service"] != "cowrie" || ev.Payload["port"] != 2222 {
		t.Fatalf("payload: %+v", ev.Payload)
	}
	if ev.OccurredAt == "" {
		t.Fatal("missing time")
	}

	kept, ok := Parse_ContainerLine(
		`{"event_type":"hit","occurred_at":"t0","payload":{"service":"own","port":9}}`,
		"cowrie",
		2222,
	)
	if !ok || kept.OccurredAt != "t0" || kept.Payload["service"] != "own" || kept.Payload["port"] != float64(9) {
		t.Fatalf("kept: %+v", kept)
	}
	if _, ok := Parse_ContainerLine("not json", "cowrie", 2222); ok {
		t.Fatal("plain text accepted")
	}
	if _, ok := Parse_ContainerLine(`{"payload":{}}`, "cowrie", 2222); ok {
		t.Fatal("missing event_type accepted")
	}
}
