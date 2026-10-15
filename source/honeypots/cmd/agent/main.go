package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"metricsd/internal/agent"
	"metricsd/internal/config"
	"metricsd/internal/texts"
)

func main() {
	root := agent.Find_Root()
	config.Load_DotEnv(root)
	fmt.Printf(texts.MsgApiBase+"\n", config.Get_BaseUrl())

	mode := "run"
	if len(os.Args) > 1 {
		mode = os.Args[1]
	}

	a, err := agent.New_Agent(root)
	if err != nil {
		fail_Exit(err.Error())
	}
	defer a.Close()

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	switch mode {
	case "pair":
		if err := a.Run_Pair(ctx); err != nil {
			fail_Exit(err.Error())
		}
	case "run", "start":
		if err := a.Run(ctx); err != nil {
			fail_Exit(err.Error())
		}
	case "help", "-h", "--help":
		fmt.Printf(texts.MsgUsage+"\n", os.Args[0])
	default:
		fmt.Printf(texts.MsgUsage+"\n", os.Args[0])
		fail_Exit("неизвестная команда: " + mode)
	}
}

func fail_Exit(message string) {
	fmt.Fprintf(os.Stderr, "[ERR] %s\n", message)
	os.Exit(1)
}
