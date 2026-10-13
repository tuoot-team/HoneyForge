package mid

import (
	"strings"
	"testing"
)

func feed_All(e *ttyLineEditor, raw string) (echo string, last ttyFeedResult) {
	var b strings.Builder
	for i := 0; i < len(raw); i++ {
		last = e.Feed(raw[i])
		b.WriteString(last.Echo)
		if last.Done || last.Redraw {
			break
		}
	}
	return b.String(), last
}

func Test_TtyBackspaceStopsAtPrompt(t *testing.T) {
	e := &ttyLineEditor{}
	_, _ = feed_All(e, "ab")
	r1 := e.Feed(127)
	if r1.Echo != "\b \b" || e.Content() != "a" {
		t.Fatalf("first bs: echo=%q content=%q", r1.Echo, e.Content())
	}
	r2 := e.Feed(127)
	if r2.Echo != "\b \b" || e.Content() != "" {
		t.Fatalf("second bs: echo=%q content=%q", r2.Echo, e.Content())
	}
	r3 := e.Feed(127)
	if r3.Echo != "" || e.Content() != "" {
		t.Fatalf("bs into prompt: echo=%q content=%q", r3.Echo, e.Content())
	}
}

func Test_TtyCtrlLRedraw(t *testing.T) {
	e := &ttyLineEditor{}
	_, _ = feed_All(e, "ls")
	r := e.Feed(12)
	if !r.Redraw || e.Content() != "ls" {
		t.Fatalf("ctrl+l: redraw=%v content=%q", r.Redraw, e.Content())
	}
}

func Test_TtyArrowKeysDoNotEcho(t *testing.T) {
	e := &ttyLineEditor{}
	_, _ = feed_All(e, "x")
	echo, _ := feed_All(e, "\x1b[D\x1b[C\x1b[A\x1b[B")
	if echo != "" || e.Content() != "x" {
		t.Fatalf("arrows leaked: echo=%q content=%q", echo, e.Content())
	}
	r := e.Feed(127)
	if r.Echo != "\b \b" || e.Content() != "" {
		t.Fatalf("bs after arrows: echo=%q content=%q", r.Echo, e.Content())
	}
	r = e.Feed(127)
	if r.Echo != "" {
		t.Fatalf("bs erased prompt after arrows: %q", r.Echo)
	}
}

func Test_TtyCtrlCharsNotBuffered(t *testing.T) {
	e := &ttyLineEditor{}
	echo, _ := feed_All(e, "\x01\x02\x05\x0c")
	// Ctrl+L stops feed_All early with Redraw; content must stay empty.
	if e.Content() != "" {
		t.Fatalf("controls in buffer: %q echo=%q", e.Content(), echo)
	}
}

func Test_TtyUTF8Backspace(t *testing.T) {
	e := &ttyLineEditor{}
	_, _ = feed_All(e, "й")
	if e.Content() != "й" {
		t.Fatalf("utf8 content=%q", e.Content())
	}
	r := e.Feed(127)
	if r.Echo != "\b \b" || e.Content() != "" {
		t.Fatalf("utf8 bs: echo=%q content=%q", r.Echo, e.Content())
	}
	r = e.Feed(127)
	if r.Echo != "" {
		t.Fatalf("utf8 bs into prompt: %q", r.Echo)
	}
}

func Test_TtyEnterAndCtrlC(t *testing.T) {
	e := &ttyLineEditor{}
	_, last := feed_All(e, "pwd\r")
	if !last.Done || last.Cancel || last.Line != "pwd" {
		t.Fatalf("enter: %+v", last)
	}
	e.Reset()
	_, last = feed_All(e, "x\x03")
	if !last.Done || !last.Cancel {
		t.Fatalf("ctrl+c: %+v", last)
	}
}
