package mid

import (
	"fmt"
	"regexp"
	"strings"

	"metricsd/internal/model"
)

var (
	rePortPlaceholder = regexp.MustCompile(`\{\{port:([a-zA-Z0-9_-]+)\}\}`)
	reCredPlaceholder = regexp.MustCompile(`\{\{cred:([a-zA-Z0-9_-]+)\.(username|password)\}\}`)
	reUserPlaceholder = regexp.MustCompile(`\{\{user\}\}`)
)

// ExpandedBaits - раскрытые bait-файлы и HTTP routes для текущего профиля.
type ExpandedBaits struct {
	Files      map[string]string
	HttpRoutes map[string][]model.HttpRoute // service_id -> routes
}

func Expand_Baits(profile model.Profile, shellUser string) ExpandedBaits {
	out := ExpandedBaits{
		Files:      map[string]string{},
		HttpRoutes: map[string][]model.HttpRoute{},
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
	for _, bait := range profile.Blocks.Baits {
		body := expand_BaitText(bait.Body, ports, creds, user)
		path := expand_BaitText(bait.Path, ports, creds, user)
		switch strings.ToLower(strings.TrimSpace(bait.Kind)) {
		case "file":
			if path == "" {
				continue
			}
			out.Files[path] = body
		case "http_route":
			sid := strings.TrimSpace(bait.ServiceID)
			if sid == "" || path == "" {
				continue
			}
			route := model.HttpRoute{
				Path:        path,
				Methods:     []string{"GET"},
				Status:      200,
				ContentType: "text/html; charset=utf-8",
				Body:        body,
			}
			out.HttpRoutes[sid] = append(out.HttpRoutes[sid], route)
		}
	}
	return out
}

func expand_BaitText(
	raw string,
	ports map[string]int,
	creds map[string]model.CredentialBlock,
	user string,
) string {
	text := reUserPlaceholder.ReplaceAllString(raw, user)
	text = rePortPlaceholder.ReplaceAllStringFunc(text, func(match string) string {
		sub := rePortPlaceholder.FindStringSubmatch(match)
		if len(sub) < 2 {
			return match
		}
		port, ok := ports[sub[1]]
		if !ok {
			return match
		}
		return fmt.Sprintf("%d", port)
	})
	text = reCredPlaceholder.ReplaceAllStringFunc(text, func(match string) string {
		sub := reCredPlaceholder.FindStringSubmatch(match)
		if len(sub) < 3 {
			return match
		}
		cred, ok := creds[sub[1]]
		if !ok {
			return match
		}
		if sub[2] == "username" {
			return cred.Username
		}
		return cred.Password
	})
	return text
}

func Apply_FileBaits(shell *FakeShell, files map[string]string) {
	if shell == nil || len(files) == 0 {
		return
	}
	for path, body := range files {
		full := path
		if !strings.HasPrefix(full, "/") {
			full = "/" + full
		}
		// {{user}} уже раскрыт; путь /home/ops/... должен совпасть с Home.
		if strings.HasPrefix(full, "/home/") && shell.Home != "" && shell.Home != "/root" {
			// если bait писал /home/ops а сессия под другим юзером - кладём в Home
			parts := strings.SplitN(strings.TrimPrefix(full, "/home/"), "/", 2)
			if len(parts) == 2 {
				full = shell.Home + "/" + parts[1]
			} else if len(parts) == 1 && parts[0] != "" {
				full = shell.Home
			}
		}
		shell.Tree[full] = body
		delete(shell.Binary, full)
		delete(shell.BinaryData, full)
		add_ParentDirs(shell.Dirs, full)
		shell.touch_Meta(full, 0xBA17)
	}
}

func Merge_HttpBaitRoutes(modules model.HttpModules, routes []model.HttpRoute) model.HttpModules {
	if len(routes) == 0 {
		return modules
	}
	existing := map[string]int{}
	for i, route := range modules.Routes.Routes {
		existing[route.Path] = i
	}
	for _, route := range routes {
		if idx, ok := existing[route.Path]; ok {
			modules.Routes.Routes[idx].Body = route.Body
			if route.ContentType != "" {
				modules.Routes.Routes[idx].ContentType = route.ContentType
			}
			continue
		}
		modules.Routes.Routes = append(modules.Routes.Routes, route)
	}
	return modules
}
