#!/bin/sh
# Nginx + опциональный Let's Encrypt, если задан TLS_DOMAIN.
# Operator API всегда на :8088 - HTTP без домена, HTTPS при TLS_DOMAIN.
# mTLS на :443 только если найден CA (MTLS_CA_FILE или /etc/honeyforge/mtls/ca.crt).
set -e

DOMAIN="$(echo "${TLS_DOMAIN:-}" | tr -d '[:space:]')"
EMAIL="$(echo "${TLS_EMAIL:-}" | tr -d '[:space:]')"

resolve_Mtls_Ca() {
	_ca="$(echo "${MTLS_CA_FILE:-}" | tr -d '[:space:]')"
	if [ -n "$_ca" ] && [ -f "$_ca" ]; then
		echo "$_ca"
		return 0
	fi
	if [ -f /etc/honeyforge/mtls/ca.crt ]; then
		echo /etc/honeyforge/mtls/ca.crt
		return 0
	fi
	echo ""
}

MTLS_CA="$(resolve_Mtls_Ca)"

mkdir -p /var/www/certbot /etc/nginx/conf.d /etc/letsencrypt
rm -f /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/tls.conf /etc/nginx/conf.d/operator.conf

write_Operator_Http() {
	cat > /etc/nginx/conf.d/operator.conf <<'EOF'
# Operator API без TLS
server {
	listen 8088;
	server_name _;

	include /etc/nginx/honeyforge/operator_locations.conf;
}
EOF
}

write_Tls_Conf() {
	_domain="$1"
	_mtls_ca="$2"
	_mtls_block=""
	if [ -n "$_mtls_ca" ]; then
		_mtls_block=$(cat <<MTLS
	# Опциональный mTLS: агент/курьер предъявляют клиентский сертификат
	ssl_client_certificate ${_mtls_ca};
	ssl_verify_client on;
MTLS
)
	fi
	cat > /etc/nginx/conf.d/tls.conf <<EOF
# Сгенерировано entrypoint при TLS_DOMAIN=${_domain}
server {
	listen 443 ssl;
	http2 on;
	server_name ${_domain};

	ssl_certificate     /etc/letsencrypt/live/${_domain}/fullchain.pem;
	ssl_certificate_key /etc/letsencrypt/live/${_domain}/privkey.pem;
	ssl_session_timeout 1d;
	ssl_session_cache shared:SSL:10m;
	ssl_protocols TLSv1.2 TLSv1.3;
${_mtls_block}
	include /etc/nginx/honeyforge/agent_locations.conf;
}

# Тот же порт 8088, что и без TLS - только уже HTTPS (без mTLS)
server {
	listen 8088 ssl;
	http2 on;
	server_name ${_domain};

	ssl_certificate     /etc/letsencrypt/live/${_domain}/fullchain.pem;
	ssl_certificate_key /etc/letsencrypt/live/${_domain}/privkey.pem;
	ssl_session_timeout 1d;
	ssl_session_cache shared:SSL:10m;
	ssl_protocols TLSv1.2 TLSv1.3;

	include /etc/nginx/honeyforge/operator_locations.conf;
}
EOF
}

obtain_Or_Skip_Cert() {
	_domain="$1"
	_email="$2"
	if [ -f "/etc/letsencrypt/live/${_domain}/fullchain.pem" ]; then
		echo "[ssl] сертификат для ${_domain} уже есть"
		return 0
	fi
	if [ -z "$_email" ]; then
		_email="admin@${_domain}"
	fi
	echo "[ssl] запрос Let's Encrypt для ${_domain} (email=${_email})"
	certbot certonly \
		--webroot \
		-w /var/www/certbot \
		-d "$_domain" \
		--email "$_email" \
		--agree-tos \
		--non-interactive \
		--rsa-key-size 2048 \
		|| {
			echo "[ssl] certbot не смог выпустить сертификат - остаёмся на HTTP"
			return 1
		}
}

renew_Loop() {
	while true; do
		sleep 43200
		certbot renew --webroot -w /var/www/certbot --quiet && nginx -s reload || true
	done
}

write_Api_Upstream() {
	_raw="$(echo "${API_BASE:-http://api:8000}" | tr -d '[:space:]')"
	_raw="${_raw%/}"
	_hostport="${_raw#http://}"
	_hostport="${_hostport#https://}"
	_hostport="${_hostport%%/*}"
	case "$_hostport" in
		""|*[!A-Za-z0-9.:_-]*)
			echo "[api] API_BASE не разобран, upstream api:8000"
			_hostport="api:8000"
			;;
	esac
	cat > /etc/nginx/conf.d/upstream.conf <<EOF
upstream honeyforge_api {
	server ${_hostport};
}
EOF
	echo "[api] /api -> ${_hostport}"
}

# Сначала HTTP operator, чтобы конфиг был валиден до выпуска сертификата.
write_Api_Upstream
write_Operator_Http

nginx
sleep 1

if [ -n "$DOMAIN" ]; then
	if obtain_Or_Skip_Cert "$DOMAIN" "$EMAIL"; then
		rm -f /etc/nginx/conf.d/operator.conf
		write_Tls_Conf "$DOMAIN" "$MTLS_CA"
		nginx -s reload
		echo "[ssl] HTTPS: :443 (агент/сайт), :8088 (operator API)"
		if [ -n "$MTLS_CA" ]; then
			echo "[ssl] mTLS на :443 включён (CA=${MTLS_CA})"
		else
			echo "[ssl] mTLS выключен (нет MTLS_CA_FILE / /etc/honeyforge/mtls/ca.crt)"
		fi
		echo "[ssl] PUBLIC_BASE_URL=https://${DOMAIN}"
		echo "[ssl] CLI API_BASE=https://${DOMAIN}:8088"
		renew_Loop &
	else
		echo "[ssl] operator остаётся HTTP :8088"
	fi
else
	echo "[ssl] TLS_DOMAIN пуст - HTTP :80 (агент), :8088 (operator)"
fi

nginx -s quit || true
sleep 1
exec nginx -g "daemon off;"
