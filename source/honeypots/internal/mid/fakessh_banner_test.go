package mid

import (
	"os"
	"path/filepath"
	"testing"

	"golang.org/x/crypto/ssh"
)

func Test_OpenSshLikeAlgos(t *testing.T) {
	cfg := openSshLikeAlgos()
	if len(cfg.KeyExchanges) == 0 || len(cfg.Ciphers) == 0 || len(cfg.MACs) == 0 {
		t.Fatalf("empty algos: %+v", cfg)
	}
	foundCurve := false
	for _, k := range cfg.KeyExchanges {
		if k == ssh.KeyExchangeCurve25519 {
			foundCurve = true
		}
		if k == ssh.KeyExchangeMLKEM768X25519 {
			t.Fatalf("ML-KEM in OpenSSH 8.9-like set: %v", cfg.KeyExchanges)
		}
	}
	if !foundCurve {
		t.Fatalf("missing curve25519: %v", cfg.KeyExchanges)
	}
}

func Test_Load_HostKeys(t *testing.T) {
	dir := t.TempDir()
	base := filepath.Join(dir, ".ssh_host_key")
	signers, err := Load_HostKeys(base)
	if err != nil {
		t.Fatal(err)
	}
	if len(signers) != 3 {
		t.Fatalf("want 3 host keys, got %d", len(signers))
	}
	for _, name := range []string{".ssh_host_ed25519", ".ssh_host_ecdsa", ".ssh_host_rsa"} {
		if _, err := os.Stat(filepath.Join(dir, name)); err != nil {
			t.Fatalf("missing %s: %v", name, err)
		}
	}
	again, err := Load_HostKeys(base)
	if err != nil {
		t.Fatal(err)
	}
	if again[0].PublicKey().Type() != signers[0].PublicKey().Type() {
		t.Fatalf("reload changed first key type")
	}
}

func Test_Ssh_Identification(t *testing.T) {
	cases := []struct {
		in   string
		want string
	}{
		{"", defaultSshIdentification},
		{"2.0", defaultSshIdentification},
		{"SSH-2.0", defaultSshIdentification},
		{"SSH-2.0-", defaultSshIdentification},
		{"SSH-1.99-OpenSSH_7.0", defaultSshIdentification},
		{"OpenSSH_8.9p1", "SSH-2.0-OpenSSH_8.9p1"},
		{"SSH-2.0-OpenSSH_8.9p1", "SSH-2.0-OpenSSH_8.9p1"},
		{"Trololo", "SSH-2.0-Trololo"},
		{
			"SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6\r\n",
			"SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6",
		},
		{
			defaultSshIdentification,
			defaultSshIdentification,
		},
	}
	for _, tc := range cases {
		got := Ssh_Identification(tc.in)
		if got != tc.want {
			t.Fatalf("Ssh_Identification(%q)=%q want %q", tc.in, got, tc.want)
		}
		if got != Ssh_Identification(Format_SshBanner(tc.in)) {
			t.Fatalf("Format round-trip changed identification for %q", tc.in)
		}
	}
}

func Test_Format_SshBanner_CRLF(t *testing.T) {
	got := Format_SshBanner("OpenSSH_9.0")
	if got != "SSH-2.0-OpenSSH_9.0\r\n" {
		t.Fatalf("got %q", got)
	}
}
