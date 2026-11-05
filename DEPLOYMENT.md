# Production deployment

Local desktop setup is complete in this checkout. Deployment requires a server/domain, TLS certificate, and its operator's credentials. This project has not been deployed publicly.

## Runtime

Use Python 3.13, Node 22+, MySQL 8.0+ (InnoDB, utf8mb4, strict mode), and a supported Redis 7+ service. Install `backend/requirements.lock.txt` and use `npm ci` with the checked-in lockfile. Linux needs the MySQL client development headers/build tools for mysqlclient. Use an unprivileged application OS account. Keep MySQL/Redis on the private network. Memurai Developer is only for the Windows development setup and must not be used in production.

Create a dedicated database named `areyouthere` and a dedicated app account granted access only to that database. Do not grant the production application access to unrelated databases. Use a separate isolated test server/account for automated tests. Never run tests against production data. Apply Django migrations during release and back up MySQL before schema changes.

## Environment

Provide secrets through the host's secret manager or an OS-protected `.env` file outside the web root. Start from `.env.example`. Configure:

```dotenv
DEBUG=0
DJANGO_SECRET_KEY=<unique-random-secret>
MYSQL_DATABASE=areyouthere
MYSQL_HOST=<private-mysql-host>
MYSQL_PORT=3306
MYSQL_USER=<dedicated-user>
MYSQL_PASSWORD=<secret>
REDIS_URL=rediss://:<secret>@<private-redis-host>:6379/0
ALLOWED_HOSTS=class.example.edu
CORS_ORIGINS=https://class.example.edu,chrome-extension://<published-extension-id>
```

The deployment proxy must remove client-supplied `X-Forwarded-Proto` and set its own trusted value. Django's production configuration redirects HTTP, uses secure cookies, and enables HSTS. Run Django's `check --deploy` in the configured production environment and resolve all warnings before exposing it. Rate limiting is per process in development; put shared rate limiting on the production reverse proxy or configure Django's cache with shared Redis.

## Application processes

Run an ASGI server, for example `daphne -b 127.0.0.1 -p 8000 config.asgi:application`, with its working directory set to `backend`. Run `python backend/manage.py run_scheduler` separately, with the project root as its working directory. Use systemd, containers with restart policies, or another process supervisor for **both**. The scheduler is safe to restart and uses transactional MySQL row locks to prevent duplicate delivery. Multiple scheduler processes can coexist, but one is sufficient for a small deployment.

The scheduler's `.runtime/scheduler-heartbeat` file should update every second. Alert if stale by more than 15 seconds. Monitor MySQL and Redis, server errors, disk capacity, and `/api/health/` (returns 503 when MySQL or Redis is unavailable). Scheduler failure does not erase schedules; due questions deliver when it returns. Allow for this recovery behavior when operating live classes.

Build the React dashboard with `npm run build`. Serve only **dist/dashboard** from Nginx or another static web server. Use SPA fallback to `index.html`. Proxy `/api/` and `/admin/` to Django and `/ws/` to the ASGI server with HTTP/1.1 Upgrade headers and an idle timeout above 60 seconds. Serve `backend/staticfiles` at `/static/` after `collectstatic`. Never expose the project root, `.env`, `.runtime`, backend source, or test reports as static files.

Example Nginx route structure, inside a TLS-configured server block:

```nginx
root /srv/areyouthere/dist/dashboard;
location / { try_files $uri $uri/ /index.html; }
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
location /admin/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
location /static/ { alias /srv/areyouthere/backend/staticfiles/; }
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 90s;
}
```

## Extension release

Set build-time `VITE_API_ORIGIN=https://class.example.edu` before `npm run build`. The build embeds that origin in both extension API clients; packaging restricts `host_permissions` to that origin and requires HTTPS away from localhost. Do not put secrets in VITE variables: the extension and dashboard are public client code.

Register the published Chrome Web Store extension ID in `CORS_ORIGINS`. Production WebSocket origins are restricted to the same explicit origins; development-only matching of unpacked extension IDs is disabled with `DEBUG=0`. Upload `dist/areyouthere-extension.zip` to the Chrome Web Store using your own developer account. Store publication, account fees, required privacy disclosures, and review require your account access and have not been performed here.

Publish a privacy notice describing account/membership data, responses, optional reasons, heartbeat timestamps, retention, and the institution's contact. Configure operational backups and an appropriate institutional retention policy. The app does not collect camera, microphone, browsing history, or screen recordings. Browser alarms can be delayed and short prompts can be missed when the side panel is closed, so instruct students to keep it open during class.

## Release verification

Use a staging MySQL database and Redis service to run backend tests and the browser suite. Confirm newly registered teachers can host immediately without gaining staff privileges; students cannot host; outsiders cannot read sessions/export data; one response commits under concurrent submissions; deadlines survive clock differences; closed-before-join questions are excluded; scheduled delivery recovers after a scheduler restart; and reconnects recover the same response from MySQL. Apply migration 0002 to remove the former approval flag from existing accounts. Check Chrome extension loading on the published ID and actual Chrome side-panel behavior. The checked-in screenshots and PLAN.md document local checks, not production verification.
