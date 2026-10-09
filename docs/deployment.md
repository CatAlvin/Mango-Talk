# Deployment and recovery

Mango Talk runs behind Nginx with HTTPS, MySQL 8, and a systemd-managed API. Each release corresponds to one complete Git commit; `/release.json` exposes the build's commit for verification. The release scripts update an existing Mango Talk installation and preserve its TLS certificate settings.

## Configure the destination

The workstation needs Git, Node.js 22.22.2 or 24.15+, OpenSSH, and Windows `tar`. The server needs Python 3.10+, venv, Git, MySQL client tools, Nginx, systemd, and `flock`.

Set up SSH authentication locally. Supply a destination explicitly:

```powershell
./scripts/deploy.ps1 -SshHost my-server `
  -RemoteProject /srv/mango-talk `
  -PublicUrl https://chat.example.com
```

Alternatively create `.deploy/local-config.json` on your workstation:

```json
{
  "sshHost": "my-server",
  "remoteProject": "/srv/mango-talk",
  "publicUrl": "https://chat.example.com"
}
```

This file is ignored by Git. Command arguments override its values. The project path must be absolute, resolve to the same directory, and end in `/mango-talk`. The public URL is an HTTPS origin without a path. Keys and passwords stay in the SSH configuration and server environment rather than this destination file.

The existing installation should have:

| Item | Configuration |
| :--- | :--- |
| Repository | Clean `main` checkout with its configured origin |
| Environment | `backend/.env`, readable by the service group |
| Nginx | `/etc/nginx/sites-available/mango-talk`, with working TLS |
| API unit | `/etc/systemd/system/mango-talk-api.service` |
| API listener | `127.0.0.1:8000`, one worker |
| Persistent files | `uploads/` and `logs/` under the project |
| Release records | `.deploy/releases/` and root-only `.deploy/backups/` |

Configure a random `JWT_SECRET_KEY` of at least 32 characters and MySQL connection parameters or `DATABASE_URL`. Deployment sets the production environment, allowed origin, and shared upload root explicitly. The service runs as `mango-talk`; the environment file has mode `0640`, while checkpoint copies have mode `0600`.

## Release a commit

Run the commands in [Validation](VALIDATION.md), check the desktop and mobile flows, then commit and push the complete change:

```powershell
git push origin main
./scripts/deploy.ps1
```

The launcher requires a clean working tree and an exact match between local HEAD and remote `main`. It runs `npm ci` and the production build, writes the commit manifest, and uploads the build with the deployment tools from that commit. An installation with pnpm alone uses a pinned npm package to execute the same commands.

On the server, deployment:

1. Acquires a lock and verifies the checkout, remote commit, and build manifest.
2. Creates a separate release and virtual environment, installs dependencies from PyPI over HTTPS, and runs backend and snapshot tests.
3. Saves the current site configuration, service unit, environment, commit, and release link.
4. Stops the API and captures a verified compressed MySQL snapshot.
5. Runs the repeatable migration and atomically switches the current-release link.
6. Installs the generated templates, checks Nginx, and restarts the API.
7. Verifies local and HTTPS database health, the exact manifest, client-route bodies, and demo resources before advancing the server checkout.

Dependencies and tests run before the service stops. During backup, migration, and restart, chat connections briefly disconnect and subsequently recover. Releases retain their own dependencies for recovery.

## Routing and logs

Nginx proxies API and WebSocket paths to the backend. Attachments have no public filesystem alias: downloads pass through authorization. Access logs contain `$uri` without query parameters or Referer; Uvicorn access logging is disabled so connection tokens are not written to request logs.

Authentication endpoints share a per-IP quota of ten requests per minute, with a ten-request burst and a JSON `429` response. HTTPS uses HSTS, content-type protection, frame restrictions, and a content security policy for the site's scripts, styles, images, and WebSocket origin. The demo route explicitly loads the client application alongside its static-resource directory.

After release, check `/health/db` and `/release.json`. In the browser, verify the login-page demo entry, direct navigation and refresh, short-screen layout, and real-account send, reconnect, reply, recall, and attachment access. Use isolated accounts for functional checks.

## Application recovery

If a check fails after switching begins, deployment restores the earlier application link and configuration. Successful deployment records the latest checkpoint in `.deploy/latest-backup`.

On the server, with your configured project location:

```bash
PROJECT=/srv/mango-talk
cat "$PROJECT/.deploy/latest-backup"
bash "$PROJECT/.deploy/current/deploy/rollback.sh" \
  "$PROJECT/.deploy/backups/CHECKPOINT"
```

Replace `CHECKPOINT` with the verified checkpoint directory. Recovery requires the checkout to match that release and have no application edits. It restores the earlier code and site configuration, while retaining compatible migrations and messages received after release. The GitHub history remains intact; a subsequent fix is committed and deployed normally.

## Database recovery

Use a database snapshot only after choosing the recovery point and accounting for subsequent writes. Stop all writers before restoring:

```bash
PROJECT=/srv/mango-talk
systemctl stop mango-talk-api.service
cd "$PROJECT/.deploy/current/backend"
.venv/bin/python ../deploy/database_snapshot.py restore \
  --backend "$PROJECT/.deploy/current/backend" \
  --snapshot "$PROJECT/.deploy/backups/CHECKPOINT/database.sql.gz" \
  --confirm-database-restore
```

Select the application version corresponding to the snapshot, check database health, and then reopen the API. Keep checkpoints outside public downloads and maintain a controlled off-server copy. Retention and restore drills belong to the installation's operating procedures.
