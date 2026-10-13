package mid

import (
	"strings"
	"unicode/utf8"
)

// Результат одного байта в line-editor (PTY raw mode).
type ttyFeedResult struct {
	Echo   string // что сразу писать в канал
	Redraw bool   // Ctrl+L: очистить экран и перерисовать prompt+буфер снаружи
	Done   bool   // Enter / Ctrl+C - строка готова
	Cancel bool   // Ctrl+C - строку не выполнять
	Line   string // готовая строка при Done
}

// Редактор строки без readline: не эхоим управляющие/CSI, backspace только по рунам ввода.
type ttyLineEditor struct {
	buf    []byte
	esc    int // 0=обычный, 1=после ESC, 2=CSI ждём финал
	utfRem int // сколько байт UTF-8 ещё ждать после стартового
}

func (e *ttyLineEditor) Reset() {
	e.buf = e.buf[:0]
	e.esc = 0
	e.utfRem = 0
}

func (e *ttyLineEditor) Content() string {
	return string(e.buf)
}

func (e *ttyLineEditor) Feed(ch byte) ttyFeedResult {
	if e.esc == 1 {
		if ch == '[' || ch == 'O' {
			e.esc = 2
			return ttyFeedResult{}
		}
		e.esc = 0
		return ttyFeedResult{}
	}
	if e.esc == 2 {
		// CSI / SS3: глотаем до финального байта, на экран не пускаем.
		if (ch >= 0x40 && ch <= 0x7e) || ch == '~' {
			e.esc = 0
		}
		return ttyFeedResult{}
	}
	if e.utfRem > 0 {
		if ch&0xc0 != 0x80 {
			e.utfRem = 0
			return e.Feed(ch)
		}
		e.buf = append(e.buf, ch)
		e.utfRem--
		return ttyFeedResult{Echo: string([]byte{ch})}
	}

	switch ch {
	case '\r', '\n':
		line := string(e.buf)
		e.Reset()
		return ttyFeedResult{Echo: "\n", Done: true, Line: line}
	case 3: // Ctrl+C
		e.Reset()
		return ttyFeedResult{Echo: "^C\n", Done: true, Cancel: true}
	case 4: // Ctrl+D на пустой строке - как exit
		if len(e.buf) == 0 {
			return ttyFeedResult{Done: true, Line: "exit"}
		}
		return ttyFeedResult{}
	case 12: // Ctrl+L - clear + redraw снаружи
		return ttyFeedResult{Redraw: true}
	case 127, 8: // Backspace / Ctrl+H
		if len(e.buf) == 0 {
			return ttyFeedResult{}
		}
		_, size := utf8.DecodeLastRune(e.buf)
		if size <= 0 {
			size = 1
		}
		e.buf = e.buf[:len(e.buf)-size]
		return ttyFeedResult{Echo: "\b \b"}
	case 21: // Ctrl+U - убить строку ввода
		if len(e.buf) == 0 {
			return ttyFeedResult{}
		}
		n := utf8.RuneCount(e.buf)
		e.buf = e.buf[:0]
		return ttyFeedResult{Echo: strings.Repeat("\b \b", n)}
	case 27: // ESC - начало стрелок/функциональных клавиш
		e.esc = 1
		return ttyFeedResult{}
	}

	if ch < 32 {
		// Остальные control не эхоим и не кладём в буфер.
		return ttyFeedResult{}
	}

	// UTF-8: стартовые байты многобайтовых рун.
	if ch >= 0x80 {
		switch {
		case ch&0xe0 == 0xc0:
			e.utfRem = 1
		case ch&0xf0 == 0xe0:
			e.utfRem = 2
		case ch&0xf8 == 0xf0:
			e.utfRem = 3
		default:
			return ttyFeedResult{}
		}
		e.buf = append(e.buf, ch)
		return ttyFeedResult{Echo: string([]byte{ch})}
	}

	e.buf = append(e.buf, ch)
	return ttyFeedResult{Echo: string([]byte{ch})}
}
