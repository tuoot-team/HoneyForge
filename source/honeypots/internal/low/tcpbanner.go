package low

import (
	"context"
	"fmt"
	"net"

	"honeyforge/honeypots/internal/model"
	"honeyforge/honeypots/internal/state"
	"honeyforge/honeypots/internal/texts"
)

type EventHandler func(model.AgentEvent)

func Start_TcpBanner(
	ctx context.Context,
	port int,
	banner string,
	serviceName string,
	onEvent EventHandler,
	debug bool,
) error {
	addr := fmt.Sprintf("0.0.0.0:%d", port)
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return err
	}
	if debug {
		fmt.Printf(texts.MsgLowStarted+"\n", port, banner)
	}

	go func() {
		<-ctx.Done()
		_ = ln.Close()
	}()

	for {
		conn, err := ln.Accept()
		if err != nil {
			select {
			case <-ctx.Done():
				if debug {
					fmt.Printf(texts.MsgLowStopped+"\n", port)
				}
				return nil
			default:
				continue
			}
		}
		go handle_Connection(conn, port, banner, serviceName, onEvent, debug)
	}
}

func handle_Connection(
	conn net.Conn,
	port int,
	banner string,
	serviceName string,
	onEvent EventHandler,
	debug bool,
) {
	defer conn.Close()

	var sourceIP *string
	var sourcePort *int
	if addr, ok := conn.RemoteAddr().(*net.TCPAddr); ok {
		ip := addr.IP.String()
		p := addr.Port
		sourceIP = &ip
		sourcePort = &p
	}

	if debug {
		fmt.Printf(texts.MsgLowConnect+"\n", derefStr(sourceIP), derefInt(sourcePort), port)
	}

	onEvent(model.AgentEvent{
		EventType:  "port_connect",
		SourceIP:   sourceIP,
		SourcePort: sourcePort,
		OccurredAt: state.Now_Iso(),
		Payload: map[string]any{
			"port":    port,
			"service": serviceName,
		},
	})

	if _, err := conn.Write([]byte(banner)); err != nil {
		return
	}
	onEvent(model.AgentEvent{
		EventType:  "banner_grab",
		SourceIP:   sourceIP,
		SourcePort: sourcePort,
		OccurredAt: state.Now_Iso(),
		Payload: map[string]any{
			"port":   port,
			"banner": banner,
		},
	})
	if debug {
		fmt.Printf(texts.MsgLowBannerSent+"\n", banner)
	}
}

func derefStr(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}

func derefInt(p *int) any {
	if p == nil {
		return nil
	}
	return *p
}
