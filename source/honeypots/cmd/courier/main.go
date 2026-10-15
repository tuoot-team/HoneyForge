package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"metricsd/internal/config"
	"metricsd/internal/courier"
	"metricsd/internal/texts"
)

func main() {
	root := courier.Find_Root()
	config.Load_DotEnv(root)
	fmt.Printf(texts.MsgApiBase+"\n", config.Get_BaseUrl())

	mode := "run"
	if len(os.Args) > 1 {
		mode = os.Args[1]
	}

	runner, err := courier.New_Runner(root)
	if err != nil {
		fail_Exit(err.Error())
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	switch mode {
	case "pair":
		if err := runner.Run_Pair(ctx); err != nil {
			fail_Exit(err.Error())
		}
	case "run", "start":
		if err := runner.Run(ctx); err != nil {
			fail_Exit(err.Error())
		}
	case "help", "-h", "--help":
		fmt.Printf("использование: %s [pair|run]\n", os.Args[0])
	default:
		fmt.Printf("использование: %s [pair|run]\n", os.Args[0])
		fail_Exit("неизвестная команда: " + mode)
	}
}

func fail_Exit(message string) {
	fmt.Fprintf(os.Stderr, "[ERR] %s\n", message)
	os.Exit(1)
}
