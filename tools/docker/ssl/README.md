# TLS certificates for the production nginx reverse proxy

The production `docker-compose.prod.yml` mounts this directory as
`/etc/nginx/ssl:ro` and expects two files:

- `cert.pem` — server certificate chain
- `key.pem`  — corresponding private key

## Local smoke

Generate self-signed placeholders so `docker-compose -f docker-compose.prod.yml up` boots end-to-end on a developer box:

```bash
cd tools/docker/ssl/
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem -out cert.pem \
  -subj "/C=US/ST=CA/L=SF/O=SceneMachine/CN=localhost"
chmod 600 key.pem
```

## Production

Replace the placeholders with certs from your CA (or Let's Encrypt via certbot). Suggested layout:

```
tools/docker/ssl/
├── cert.pem  -> /etc/letsencrypt/live/scenemachine.ai/fullchain.pem
├── key.pem   -> /etc/letsencrypt/live/scenemachine.ai/privkey.pem
└── README.md
```

Renewal hook:

```bash
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## Why this file exists

Before 2026-05-21, `docker-compose.prod.yml` referenced `./tools/docker/ssl/` and `./tools/docker/nginx.conf` but neither was tracked in the repo, so `docker-compose -f docker-compose.prod.yml up nginx` failed with `bind source path does not exist`. The production deploy was broken until this directory + the sibling `nginx.conf` landed. Tracked as P0-9 in `docs/INVENTORY_DEFECTS.md`.

`cert.pem` and `key.pem` are deliberately NOT committed — generate them locally for smoke testing, and inject real ones via your deploy pipeline.
