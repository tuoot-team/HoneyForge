package mid

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os/exec"
	"regexp"
	"strings"

	"metricsd/internal/model"
	"metricsd/internal/state"
	"metricsd/internal/texts"
)

var containerImagePattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,199}$`)

func Check_Image(image string) (string, error) {
	image = strings.TrimSpace(image)
	if !containerImagePattern.MatchString(image) || strings.Contains(image, "..") {
		return "", fmt.Errorf(texts.MsgContainerBadImage, image)
	}
	return image, nil
}

func Container_Name(serviceID string) string {
	var b strings.Builder
	b.WriteString("hf-")
	for _, r := range serviceID {
		switch {
		case r >= 'a' && r <= 'z', r >= 'A' && r <= 'Z', r >= '0' && r <= '9', r == '_', r == '.', r == '-':
			b.WriteRune(r)
		default:
			b.WriteByte('-')
		}
	}
	name := b.String()
	if name == "hf-" {
		name = "hf-container"
	}
	if len(name) > 60 {
		name = name[:60]
	}
	return name
}

func Parse_ContainerLine(line, serviceID string, port int) (model.AgentEvent, bool) {
	line = strings.TrimSpace(line)
	if line == "" || line[0] != '{' {
		return model.AgentEvent{}, false
	}
	var raw map[string]any
	if err := json.Unmarshal([]byte(line), &raw); err != nil {
		return model.AgentEvent{}, false
	}
	eventType, _ := raw["event_type"].(string)
	eventType = strings.TrimSpace(eventType)
	if eventType == "" {
		return model.AgentEvent{}, false
	}
	ev := model.AgentEvent{
		EventType:  eventType,
		OccurredAt: state.Now_Iso(),
		Payload:    map[string]any{},
	}
	if ip, ok := raw["source_ip"].(string); ok && ip != "" {
		ev.SourceIP = &ip
	}
	if n, ok := raw["source_port"].(float64); ok {
		p := int(n)
		ev.SourcePort = &p
	}
	if payload, ok := raw["payload"].(map[string]any); ok {
		ev.Payload = payload
	}
	if _, ok := ev.Payload["service"]; !ok {
		ev.Payload["service"] = serviceID
	}
	if _, ok := ev.Payload["port"]; !ok {
		ev.Payload["port"] = port
	}
	if when, ok := raw["occurred_at"].(string); ok && strings.TrimSpace(when) != "" {
		ev.OccurredAt = when
	}
	return ev, true
}

func find_Runtime() (string, error) {
	if path, err := exec.LookPath("docker"); err == nil {
		return path, nil
	}
	if path, err := exec.LookPath("podman"); err == nil {
		return path, nil
	}
	return "", fmt.Errorf("%s", texts.MsgContainerNoRuntime)
}

func Start_Container(
	ctx context.Context,
	hostPort int,
	serviceID string,
	modules model.ContainerModules,
	onEvent func(model.AgentEvent),
	debug bool,
) error {
	image, err := Check_Image(modules.Image)
	if err != nil {
		return err
	}
	runtime, err := find_Runtime()
	if err != nil {
		return err
	}
	containerPort := modules.ContainerPort
	if containerPort <= 0 {
		containerPort = hostPort
	}
	name := Container_Name(serviceID)
	_ = exec.Command(runtime, "rm", "-f", name).Run()
	pull := exec.CommandContext(ctx, runtime, "pull", image)
	pullOut, pullErr := pull.CombinedOutput()
	if pullErr != nil {
		detail := strings.TrimSpace(string(pullOut))
		if detail == "" {
			detail = pullErr.Error()
		}
		return fmt.Errorf(texts.MsgContainerPullFail, image, detail)
	}
	if ctx.Err() != nil {
		return ctx.Err()
	}
	publish := fmt.Sprintf("%d:%d", hostPort, containerPort)
	cmd := exec.Command(runtime, "run", "--rm", "--name", name, "-p", publish, image)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf(texts.MsgContainerRunFail, name, err.Error())
	}
	cmd.Stderr = io.Discard
	if err := cmd.Start(); err != nil {
		return fmt.Errorf(texts.MsgContainerRunFail, name, err.Error())
	}
	// Отмена профиля останавливает контейнер, даже если docker run ещё читает stdout.
	stopped := make(chan struct{})
	go func() {
		select {
		case <-ctx.Done():
			_ = exec.Command(runtime, "stop", "-t", "2", name).Run()
		case <-stopped:
		}
	}()
	read_ContainerStdout(stdout, serviceID, hostPort, onEvent, debug)
	waitErr := cmd.Wait()
	close(stopped)
	if ctx.Err() != nil {
		return ctx.Err()
	}
	if waitErr != nil {
		return fmt.Errorf(texts.MsgContainerRunFail, name, waitErr.Error())
	}
	return nil
}

func read_ContainerStdout(
	stdout io.Reader,
	serviceID string,
	port int,
	onEvent func(model.AgentEvent),
	debug bool,
) {
	scan := bufio.NewScanner(stdout)
	scan.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	for scan.Scan() {
		line := scan.Text()
		ev, ok := Parse_ContainerLine(line, serviceID, port)
		if !ok {
			if debug && strings.TrimSpace(line) != "" {
				fmt.Printf("%s\n", line)
			}
			continue
		}
		onEvent(ev)
	}
}
