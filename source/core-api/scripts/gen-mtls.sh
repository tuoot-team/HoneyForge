#!/bin/sh
# Демо CA + клиентский сертификат для опционального mTLS на :443.
# Результат: source/core-api/mtls/{ca.crt,ca.key,client.crt,client.key}
set -eu

root="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
out="${root}/mtls"
mkdir -p "$out"
cd "$out"

days="${MTLS_DAYS:-825}"
cn_ca="${MTLS_CA_CN:-HoneyForge mTLS CA}"
cn_client="${MTLS_CLIENT_CN:-metricsd-client}"

if [ -f ca.crt ] && [ "${MTLS_FORCE:-}" != "1" ]; then
	echo "уже есть $out/ca.crt (MTLS_FORCE=1 чтобы перевыпустить)" >&2
	exit 0
fi

openssl req -x509 -newkey rsa:2048 -nodes \
	-keyout ca.key -out ca.crt -days "$days" \
	-subj "/CN=${cn_ca}"

openssl req -newkey rsa:2048 -nodes \
	-keyout client.key -out client.csr \
	-subj "/CN=${cn_client}"

ext_file="${out}/client.ext"
cat > "$ext_file" <<EOF
basicConstraints=CA:FALSE
keyUsage=digitalSignature
extendedKeyUsage=clientAuth
EOF

openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
	-out client.crt -days "$days" -extfile "$ext_file"

rm -f client.csr ca.srl "$ext_file"
chmod 600 ca.key client.key
chmod 644 ca.crt client.crt

echo "готово: $out"
echo "  центр: ca.crt в ./mtls (compose volume), MTLS_CA_FILE=/etc/honeyforge/mtls/ca.crt"
echo "  агент/курьер: client.crt + client.key (+ TLS_CA при необходимости)"
echo "  TLS_CLIENT_CERT=.../client.crt TLS_CLIENT_KEY=.../client.key"
