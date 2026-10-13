apt update
systemctl restart nginx
tail -n 50 /var/log/auth.log
