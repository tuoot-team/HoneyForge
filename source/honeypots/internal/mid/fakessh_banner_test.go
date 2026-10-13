package mid

import "testing"

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
