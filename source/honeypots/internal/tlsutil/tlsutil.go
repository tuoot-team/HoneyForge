package tlsutil

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"

	"metricsd/internal/texts"
)

// Load_TLSConfigFromEnv собирает tls.Config из TLS_CA / TLS_CLIENT_CERT / TLS_CLIENT_KEY.
// Ничего не задано → nil (системные корни, без клиентского сертификата).
func Load_TLSConfigFromEnv() (*tls.Config, error) {
	caPath := strings.TrimSpace(os.Getenv("TLS_CA"))
	certPath := strings.TrimSpace(os.Getenv("TLS_CLIENT_CERT"))
	keyPath := strings.TrimSpace(os.Getenv("TLS_CLIENT_KEY"))
	if caPath == "" && certPath == "" && keyPath == "" {
		return nil, nil
	}
	if (certPath == "") != (keyPath == "") {
		return nil, fmt.Errorf("%s", texts.MsgErrTLSPair)
	}
	cfg := &tls.Config{
		MinVersion: tls.VersionTLS12,
	}
	if caPath != "" {
		pem, err := os.ReadFile(caPath)
		if err != nil {
			return nil, fmt.Errorf(texts.MsgErrTLSCA, err)
		}
		pool, err := x509.SystemCertPool()
		if err != nil || pool == nil {
			pool = x509.NewCertPool()
		}
		if !pool.AppendCertsFromPEM(pem) {
			return nil, fmt.Errorf("%s", texts.MsgErrTLSCAParse)
		}
		cfg.RootCAs = pool
	}
	if certPath != "" {
		cert, err := tls.LoadX509KeyPair(certPath, keyPath)
		if err != nil {
			return nil, fmt.Errorf(texts.MsgErrTLSClient, err)
		}
		cfg.Certificates = []tls.Certificate{cert}
	}
	return cfg, nil
}

// New_HTTPClient - http.Client с опциональным mTLS / своим CA.
func New_HTTPClient(timeout time.Duration) (*http.Client, error) {
	cfg, err := Load_TLSConfigFromEnv()
	if err != nil {
		return nil, err
	}
	client := &http.Client{Timeout: timeout}
	if cfg != nil {
		client.Transport = &http.Transport{TLSClientConfig: cfg}
	}
	return client, nil
}
