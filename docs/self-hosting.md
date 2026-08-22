# 🏠 Self-hosting the dashboard

The dashboard is a read-only Flask view over a SQLite result database. A production
deployment should run Gunicorn on loopback and place TLS, authentication, and any URL
prefix at a reverse proxy.

## 📦 Portable layout

One conventional layout is:

```text
/opt/vast-benchmarking/          application checkout or virtual environment
/var/lib/vast-benchmarking/      benchmarks.sqlite and durable local state
```

Keep the database outside replaceable application directories, and back it up before
upgrading or changing the schema.

## ⚙️ Run with Gunicorn

```bash
uv sync --extra server
uv run gunicorn \
  --workers 2 \
  --bind 127.0.0.1:8080 \
  "vast_benchmarking.web:create_app('/var/lib/vast-benchmarking/benchmarks.sqlite')"
```

The tracked files in `deploy/` are portable examples. Review their user, group, paths,
port, and environment before installing them; they are not drop-in declarations of a
particular host.

## 🌐 Reverse proxy

Proxy an HTTPS route to the loopback listener. When serving below a path prefix such as
`/benchmarks/`, forward the original scheme, host, and prefix headers so Flask generates
correct links. Restrict access at the proxy if machine inventory or pricing data should
not be public.

## ✅ Verification

After a deployment:

1. Confirm the service is running as the intended unprivileged account.
2. Check loopback `/healthz`.
3. Check the externally routed `/healthz`.
4. Load representative HTML, JavaScript, CSS, fonts, artwork, and favicon assets.
5. Confirm the accepted/stored counts against the SQLite database.
6. Verify the durable database survived the application update.

The Docker Compose dashboard is suitable for local evaluation:

```bash
docker compose up dashboard
```

It binds port `8080` on the Docker host. Add an explicit firewall or loopback-only port
mapping when external access is not intended.
