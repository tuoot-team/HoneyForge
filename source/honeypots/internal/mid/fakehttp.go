package mid

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"strconv"
	"strings"
	"time"

	agentauth "metricsd/internal/auth"
	"metricsd/internal/model"
	"metricsd/internal/state"
)

type HttpService struct {
	ServiceID   string
	Port        int
	Modules     model.HttpModules
	Credentials []model.CredentialBlock
	AuthStore   *agentauth.Store
	OnEvent     EventHandler
	Debug       bool
	Tokens      *HoneytokenRegistry
}

func (s *HttpService) ServeHTTP(writer http.ResponseWriter, request *http.Request) {
	sourceIP, sourcePort := http_Source(request.RemoteAddr)
	s.OnEvent(model.AgentEvent{
		EventType:  "http_request",
		SourceIP:   sourceIP,
		SourcePort: sourcePort,
		OccurredAt: state.Now_Iso(),
		Payload: map[string]any{
			"service":    s.ServiceID,
			"port":       s.Port,
			"method":     request.Method,
			"path":       request.URL.Path,
			"query":      request.URL.RawQuery,
			"user_agent": request.UserAgent(),
		},
	})
	if meta, ok := s.Tokens.Match_HTTP(s.ServiceID, request.URL.Path); ok {
		Emit_HoneytokenHit(s.OnEvent, sourceIP, sourcePort, meta, "request", map[string]any{
			"service": s.ServiceID,
			"port":    s.Port,
			"path":    request.URL.Path,
		})
	}

	personality := s.Modules.Personality
	if personality.IsEnabled() {
		if personality.Server != "" {
			writer.Header().Set("Server", personality.Server)
		}
		for key, value := range personality.Headers {
			writer.Header().Set(key, value)
		}
	}

	authModule := s.Modules.Auth
	if authModule.IsEnabled(false) && path_Matches(request.URL.Path, authModule.Path) {
		if !s.authorize(writer, request, sourceIP, sourcePort) {
			return
		}
	}

	for _, route := range s.Modules.Routes.Routes {
		if route.Path != request.URL.Path || !method_Allowed(route.Methods, request.Method) {
			continue
		}
		if route.ContentType != "" {
			writer.Header().Set("Content-Type", route.ContentType)
		}
		status := route.Status
		if status == 0 {
			status = http.StatusOK
		}
		writer.WriteHeader(status)
		_, _ = writer.Write([]byte(route.Body))
		return
	}

	status := s.Modules.Routes.DefaultStatus
	if status == 0 {
		status = http.StatusNotFound
	}
	writer.WriteHeader(status)
	_, _ = writer.Write([]byte(s.Modules.Routes.DefaultBody))
}

func (s *HttpService) authorize(
	writer http.ResponseWriter,
	request *http.Request,
	sourceIP *string,
	sourcePort *int,
) bool {
	authModule := s.Modules.Auth
	username, password, hasCredentials := request.BasicAuth()
	realm := authModule.Realm
	if realm == "" {
		realm = "Restricted"
	}
	if !hasCredentials {
		writer.Header().Set("WWW-Authenticate", fmt.Sprintf(`Basic realm="%s"`, realm))
		http.Error(writer, http.StatusText(http.StatusUnauthorized), http.StatusUnauthorized)
		return false
	}
	delay := Pick_AuthDelay(authModule.DelayMsMin, authModule.DelayMsMax)
	if delay > 0 {
		time.Sleep(delay)
	}
	ip := ""
	if sourceIP != nil {
		ip = *sourceIP
	}
	success := s.AuthStore.Evaluate(
		s.ServiceID,
		ip,
		username,
		password,
		authModule,
		s.Credentials,
	)
	s.OnEvent(model.AgentEvent{
		EventType:  "auth_attempt",
		SourceIP:   sourceIP,
		SourcePort: sourcePort,
		OccurredAt: state.Now_Iso(),
		Payload: map[string]any{
			"username": username,
			"password": password,
			"service":  s.ServiceID,
			"success":  success,
			"protocol": "http",
		},
	})
	if meta, ok := s.Tokens.Match_Cred(username, password); ok {
		Emit_HoneytokenHit(s.OnEvent, sourceIP, sourcePort, meta, "auth", map[string]any{
			"service": s.ServiceID,
			"port":    s.Port,
		})
	}
	if success {
		return true
	}
	writer.Header().Set("WWW-Authenticate", fmt.Sprintf(`Basic realm="%s"`, realm))
	http.Error(writer, http.StatusText(http.StatusUnauthorized), http.StatusUnauthorized)
	return false
}

func path_Matches(requestPath string, authPath string) bool {
	if authPath == "" || authPath == "/" {
		return true
	}
	return requestPath == authPath || strings.HasPrefix(requestPath, authPath+"/")
}

func method_Allowed(methods []string, requestMethod string) bool {
	if len(methods) == 0 {
		return requestMethod == http.MethodGet
	}
	for _, method := range methods {
		if strings.EqualFold(method, requestMethod) {
			return true
		}
	}
	return false
}

func http_Source(remoteAddr string) (*string, *int) {
	host, rawPort, err := net.SplitHostPort(remoteAddr)
	if err != nil {
		return nil, nil
	}
	port, err := strconv.Atoi(rawPort)
	if err != nil {
		return &host, nil
	}
	return &host, &port
}

func Start_FakeHttp(
	ctx context.Context,
	serviceID string,
	port int,
	modules model.HttpModules,
	credentials []model.CredentialBlock,
	authStore *agentauth.Store,
	onEvent EventHandler,
	debug bool,
	tokens *HoneytokenRegistry,
) error {
	handler := &HttpService{
		ServiceID:   serviceID,
		Port:        port,
		Modules:     modules,
		Credentials: credentials,
		AuthStore:   authStore,
		OnEvent:     onEvent,
		Debug:       debug,
		Tokens:      tokens,
	}
	server := &http.Server{
		Addr:              fmt.Sprintf("0.0.0.0:%d", port),
		Handler:           handler,
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       30 * time.Second,
	}
	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = server.Shutdown(shutdownCtx)
	}()
	err := server.ListenAndServe()
	if err == http.ErrServerClosed {
		return nil
	}
	return err
}
