package tlsutil

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func Test_Load_TLSConfigFromEnv_Empty(t *testing.T) {
	t.Setenv("TLS_CA", "")
	t.Setenv("TLS_CLIENT_CERT", "")
	t.Setenv("TLS_CLIENT_KEY", "")
	cfg, err := Load_TLSConfigFromEnv()
	if err != nil {
		t.Fatal(err)
	}
	if cfg != nil {
		t.Fatalf("expected nil config, got %#v", cfg)
	}
}

func Test_Load_TLSConfigFromEnv_PairRequired(t *testing.T) {
	t.Setenv("TLS_CLIENT_CERT", "/tmp/x.crt")
	t.Setenv("TLS_CLIENT_KEY", "")
	t.Setenv("TLS_CA", "")
	_, err := Load_TLSConfigFromEnv()
	if err == nil {
		t.Fatal("expected error for unpaired cert")
	}
}

func Test_Load_TLSConfigFromEnv_ClientCert(t *testing.T) {
	dir := t.TempDir()
	certPath, keyPath := write_TestClientPair(t, dir)
	t.Setenv("TLS_CA", "")
	t.Setenv("TLS_CLIENT_CERT", certPath)
	t.Setenv("TLS_CLIENT_KEY", keyPath)
	cfg, err := Load_TLSConfigFromEnv()
	if err != nil {
		t.Fatal(err)
	}
	if cfg == nil || len(cfg.Certificates) != 1 {
		t.Fatalf("expected client cert: %#v", cfg)
	}
}

func write_TestClientPair(t *testing.T, dir string) (string, string) {
	t.Helper()
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	tmpl := &x509.Certificate{
		SerialNumber: big.NewInt(1),
		Subject:      pkix.Name{CommonName: "test-client"},
		NotBefore:    time.Now().Add(-time.Hour),
		NotAfter:     time.Now().Add(24 * time.Hour),
		KeyUsage:     x509.KeyUsageDigitalSignature,
		ExtKeyUsage:  []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth},
	}
	der, err := x509.CreateCertificate(rand.Reader, tmpl, tmpl, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	certPath := filepath.Join(dir, "client.crt")
	keyPath := filepath.Join(dir, "client.key")
	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der})
	keyDER, err := x509.MarshalECPrivateKey(key)
	if err != nil {
		t.Fatal(err)
	}
	keyPEM := pem.EncodeToMemory(&pem.Block{Type: "EC PRIVATE KEY", Bytes: keyDER})
	if err := os.WriteFile(certPath, certPEM, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(keyPath, keyPEM, 0o600); err != nil {
		t.Fatal(err)
	}
	return certPath, keyPath
}
