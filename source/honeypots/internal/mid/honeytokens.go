package mid

import (
	"strings"

	"metricsd/internal/model"
	"metricsd/internal/state"
)

// HoneytokenMeta - метаданные canary без секрета в событии.
type HoneytokenMeta struct {
	ID   string
	Kind string
}

// HoneytokenRegistry - раскрытые токены профиля для детекции hit.
type HoneytokenRegistry struct {
	Files      map[string]HoneytokenMeta // абсолютный FS path
	HTTP       map[string]HoneytokenMeta // serviceID\0path
	Creds      map[string]HoneytokenMeta // username\0password
	PlantFiles map[string]string
	PlantHTTP  map[string][]model.HttpRoute // service_id -> routes
}

func Expand_Honeytokens(profile model.Profile, shellUser string) *HoneytokenRegistry {
	out := &HoneytokenRegistry{
		Files:      map[string]HoneytokenMeta{},
		HTTP:       map[string]HoneytokenMeta{},
		Creds:      map[string]HoneytokenMeta{},
		PlantFiles: map[string]string{},
		PlantHTTP:  map[string][]model.HttpRoute{},
	}
	ports := map[string]int{}
	creds := map[string]model.CredentialBlock{}
	for _, svc := range profile.Blocks.Services {
		id := svc.ID
		if id == "" {
			id = svc.Type
		}
		ports[id] = svc.Port
	}
	for _, cred := range profile.Blocks.Credentials {
		creds[cred.ID] = cred
	}
	user := strings.TrimSpace(shellUser)
	if user == "" {
		user = "ops"
	}
	for _, token := range profile.Blocks.Honeytokens {
		id := strings.TrimSpace(token.ID)
		if id == "" {
			continue
		}
		kind := strings.ToLower(strings.TrimSpace(token.Kind))
		path := expand_BaitText(token.Path, ports, creds, user)
		body := expand_BaitText(token.Body, ports, creds, user)
		meta := HoneytokenMeta{ID: id, Kind: kind}
		switch kind {
		case "file", "key":
			if path == "" {
				continue
			}
			full := normalize_FsPath(path)
			out.Files[full] = meta
			if body != "" {
				out.PlantFiles[full] = body
			}
		case "url":
			sid := strings.TrimSpace(token.ServiceID)
			if sid == "" || path == "" {
				continue
			}
			out.HTTP[http_TokenKey(sid, path)] = meta
			routeBody := body
			if routeBody == "" {
				routeBody = "ok"
			}
			out.PlantHTTP[sid] = append(out.PlantHTTP[sid], model.HttpRoute{
				Path:        path,
				Methods:     []string{"GET"},
				Status:      200,
				ContentType: "text/html; charset=utf-8",
				Body:        routeBody,
			})
		case "credential":
			userName := expand_BaitText(token.Username, ports, creds, user)
			pass := expand_BaitText(token.Password, ports, creds, user)
			if userName == "" || pass == "" {
				continue
			}
			out.Creds[cred_TokenKey(userName, pass)] = meta
			if path != "" && body != "" {
				full := normalize_FsPath(path)
				out.Files[full] = meta
				out.PlantFiles[full] = body
			}
		}
	}
	return out
}

func normalize_FsPath(path string) string {
	full := path
	if !strings.HasPrefix(full, "/") {
		full = "/" + full
	}
	return full
}

func http_TokenKey(serviceID, path string) string {
	return serviceID + "\x00" + path
}

func cred_TokenKey(username, password string) string {
	return username + "\x00" + password
}

// Remap_TokenFilesForHome - пути /home/<any>/... → shell.Home (как Apply_FileBaits).
func Remap_TokenFilesForHome(files map[string]HoneytokenMeta, home string) map[string]HoneytokenMeta {
	if home == "" || home == "/root" || len(files) == 0 {
		return files
	}
	out := make(map[string]HoneytokenMeta, len(files))
	for path, meta := range files {
		full := remap_HomeFilePath(path, home)
		out[full] = meta
	}
	return out
}

func remap_HomeFilePath(full, home string) string {
	if !strings.HasPrefix(full, "/home/") {
		return full
	}
	parts := strings.SplitN(strings.TrimPrefix(full, "/home/"), "/", 2)
	if len(parts) == 2 {
		return home + "/" + parts[1]
	}
	if len(parts) == 1 && parts[0] != "" {
		return home
	}
	return full
}

func Apply_HoneytokenFiles(shell *FakeShell, registry *HoneytokenRegistry) {
	if shell == nil || registry == nil {
		return
	}
	if len(registry.PlantFiles) > 0 {
		Apply_FileBaits(shell, registry.PlantFiles)
	}
	shell.TokenFiles = Remap_TokenFilesForHome(registry.Files, shell.Home)
}

func Emit_HoneytokenHit(
	onEvent EventHandler,
	sourceIP *string,
	sourcePort *int,
	meta HoneytokenMeta,
	trigger string,
	extra map[string]any,
) {
	if onEvent == nil || meta.ID == "" {
		return
	}
	payload := map[string]any{
		"token_id": meta.ID,
		"kind":     meta.Kind,
		"trigger":  trigger,
	}
	for key, value := range extra {
		if value == nil {
			continue
		}
		payload[key] = value
	}
	onEvent(model.AgentEvent{
		EventType:  "honeytoken_hit",
		SourceIP:   sourceIP,
		SourcePort: sourcePort,
		OccurredAt: state.Now_Iso(),
		Payload:    payload,
	})
}

func (r *HoneytokenRegistry) Match_HTTP(serviceID, path string) (HoneytokenMeta, bool) {
	if r == nil {
		return HoneytokenMeta{}, false
	}
	meta, ok := r.HTTP[http_TokenKey(serviceID, path)]
	return meta, ok
}

func (r *HoneytokenRegistry) Match_Cred(username, password string) (HoneytokenMeta, bool) {
	if r == nil {
		return HoneytokenMeta{}, false
	}
	meta, ok := r.Creds[cred_TokenKey(username, password)]
	return meta, ok
}

func Merge_HttpTokenRoutes(modules model.HttpModules, routes []model.HttpRoute) model.HttpModules {
	return Merge_HttpBaitRoutes(modules, routes)
}
