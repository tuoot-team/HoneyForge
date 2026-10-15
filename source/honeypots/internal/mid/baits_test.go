package mid

import (
	"strings"
	"testing"

	"metricsd/internal/model"
)

func Test_Expand_Baits(t *testing.T) {
	on := true
	profile := model.Profile{
		Blocks: model.ProfileBlocks{
			Credentials: []model.CredentialBlock{
				{ID: "ops-main", Username: "ops", Password: "secret"},
			},
			Services: []model.ServiceBlock{
				{Type: "http", ID: "http-main", Port: 8080, Enabled: &on},
				{Type: "postgres", ID: "pg-main", Port: 5432, Enabled: &on},
			},
			Baits: []model.BaitBlock{
				{
					Kind: "file",
					Path: "/home/{{user}}/NOTES.txt",
					Body: "portal http://127.0.0.1:{{port:http-main}} db={{port:pg-main}} u={{cred:ops-main.username}} p={{cred:ops-main.password}}",
				},
				{
					Kind:      "http_route",
					ServiceID: "http-main",
					Path:      "/internal",
					Body:      "pg {{port:pg-main}}",
				},
			},
		},
	}
	got := Expand_Baits(profile, "ops")
	notes := got.Files["/home/ops/NOTES.txt"]
	if !strings.Contains(notes, ":8080") || !strings.Contains(notes, "db=5432") {
		t.Fatalf("ports: %q", notes)
	}
	if !strings.Contains(notes, "u=ops") || !strings.Contains(notes, "p=secret") {
		t.Fatalf("creds: %q", notes)
	}
	routes := got.HttpRoutes["http-main"]
	if len(routes) != 1 || routes[0].Path != "/internal" {
		t.Fatalf("routes: %+v", routes)
	}
	if !strings.Contains(routes[0].Body, "5432") {
		t.Fatalf("route body: %q", routes[0].Body)
	}
}
