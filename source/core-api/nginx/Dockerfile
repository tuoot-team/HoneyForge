FROM nginx:1.27-alpine

RUN apk add --no-cache certbot openssl bash

COPY docker-entrypoint.sh /honeyforge-entrypoint.sh
COPY includes /etc/nginx/honeyforge
COPY nginx.conf /etc/nginx/nginx.conf

RUN chmod +x /honeyforge-entrypoint.sh \
	&& mkdir -p /var/www/certbot /etc/nginx/conf.d

EXPOSE 80 443 8088

ENTRYPOINT ["/honeyforge-entrypoint.sh"]
