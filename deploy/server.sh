#!/usr/bin/env bash
# Run as root on ChengLanServer. The Windows launcher uploads a commit-bound build.
set -Eeuo pipefail
umask 022

PROJECT=/home/projects/mango-talk
SITE=/etc/nginx/sites-available/mango-talk
UNIT=/etc/systemd/system/mango-talk-api.service
SERVICE=mango-talk-api.service
TOOLS=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REVISION=${1:?Usage: server.sh COMMIT FRONTEND_TAR_GZ}
ARTIFACT=${2:?Usage: server.sh COMMIT FRONTEND_TAR_GZ}

[[ $EUID == 0 ]] || { echo 'Run this script as root.' >&2; exit 1; }
[[ $REVISION =~ ^[0-9a-f]{40}$ ]] || { echo 'A complete Git commit hash is required.' >&2; exit 1; }
[[ $(realpath "$PROJECT") == /home/projects/mango-talk ]] || exit 1
[[ -f $SITE && -f $UNIT && -f $PROJECT/backend/.env && -f $ARTIFACT ]] || exit 1
for tool in git python3 curl nginx systemctl mysqldump mysql flock runuser; do
    command -v "$tool" >/dev/null || { echo "Missing deployment dependency: $tool" >&2; exit 1; }
done
export APP_ENV=production
export CORS_ORIGINS=https://mango-talk.chenglan.tech
export UPLOAD_ROOT="$PROJECT/uploads"
mkdir -p "$PROJECT/.deploy"
exec 9>"$PROJECT/.deploy/deployment.lock"
flock -n 9 || { echo 'Another Mango Talk deployment is running.' >&2; exit 1; }

[[ $(git -C "$PROJECT" branch --show-current) == main ]] || { echo 'The server checkout must be on main.' >&2; exit 1; }
[[ -z $(git -C "$PROJECT" status --porcelain -- . ':(exclude).deploy') ]] || { echo 'The server checkout contains local changes; deployment stopped.' >&2; exit 1; }
git -C "$PROJECT" fetch origin main
[[ $(git -C "$PROJECT" rev-parse origin/main) == "$REVISION" ]] || { echo 'The requested commit does not match GitHub main.' >&2; exit 1; }
OLD_REVISION=$(git -C "$PROJECT" rev-parse HEAD)
git -C "$PROJECT" merge-base --is-ancestor "$OLD_REVISION" "$REVISION" || { echo 'Deployment requires a fast-forward from the server checkout.' >&2; exit 1; }

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
RELEASE="$PROJECT/.deploy/releases/$STAMP-${REVISION:0:12}"
BACKUP="$PROJECT/.deploy/backups/$STAMP-${REVISION:0:12}"
mkdir -p "$RELEASE" "$BACKUP"
chmod 700 "$BACKUP"
git -C "$PROJECT" archive "$REVISION" | tar -x -C "$RELEASE"
mkdir -p "$RELEASE/frontend/dist"
python3 - "$ARTIFACT" "$RELEASE/frontend/dist" "$REVISION" <<'PY'
import json
from pathlib import Path
import sys
import tarfile

destination = Path(sys.argv[2]).resolve()
with tarfile.open(sys.argv[1], "r:gz") as archive:
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if not target.is_relative_to(destination) or not (member.isfile() or member.isdir()):
            raise SystemExit("Unsafe frontend archive entry")
    archive.extractall(destination)
manifest = json.loads((destination / "release.json").read_text())
if manifest["commit"] != sys.argv[3] or not (destination / "index.html").is_file():
    raise SystemExit("Frontend artifact does not belong to the requested commit")
PY

ln -s "$PROJECT/backend/.env" "$RELEASE/backend/.env"
python3 -m venv "$RELEASE/backend/.venv"
PYTHON="$RELEASE/backend/.venv/bin/python"
"$PYTHON" -m pip install --disable-pip-version-check -r "$RELEASE/backend/requirements.txt" -r "$RELEASE/backend/requirements-dev.txt"
(
    cd "$RELEASE/backend"
    "$PYTHON" -m pytest -q
)
"$PYTHON" -m unittest discover -s "$RELEASE/deploy" -p 'test_*.py' -q
"$PYTHON" -m compileall -q "$RELEASE/backend/app"
(
    cd "$RELEASE/backend"
    "$PYTHON" -c 'from app.core.config import settings; assert len(settings.JWT_SECRET_KEY) >= 32, "Production JWT_SECRET_KEY must contain at least 32 characters"'
)

# Preserve the active certificate configuration; this certificate also serves
# another site and is intentionally neither recreated nor reconfigured here.
python3 - "$TOOLS" "$PROJECT" "$SITE" "$BACKUP" <<'PY'
from pathlib import Path
import re
import sys

tools, project, site, backup = map(Path, sys.argv[1:])
current = site.read_text()
values = {"@PROJECT@": str(project)}
for key, directive in (("@CERTIFICATE@", "ssl_certificate"), ("@CERTIFICATE_KEY@", "ssl_certificate_key")):
    match = re.search(r"^\s*" + directive + r"\s+([^;]+);", current, flags=re.M)
    if not match or not Path(match[1].strip()).is_file():
        raise SystemExit("The existing TLS certificate configuration is unavailable")
    values[key] = match[1].strip()
for source, name in (("mango-talk.nginx.template", "next.nginx"), ("mango-talk-api.service.template", "next.service")):
    content = (tools / source).read_text()
    for token, value in values.items():
        content = content.replace(token, value)
    (backup / name).write_text(content)
PY

cp -a "$SITE" "$BACKUP/previous.nginx"
cp -a "$UNIT" "$BACKUP/previous.service"
cp "$PROJECT/backend/.env" "$BACKUP/production.env"
chmod 600 "$BACKUP/production.env"
printf '%s\n' "$OLD_REVISION" >"$BACKUP/previous.commit"
printf '%s\n' "$REVISION" >"$BACKUP/release.commit"
readlink "$PROJECT/.deploy/current" >"$BACKUP/previous.release" || true
printf '%s\n' "$RELEASE" >"$BACKUP/release.path"
systemctl is-active --quiet "$SERVICE" && WAS_ACTIVE=1 || WAS_ACTIVE=0
printf '%s\n' "$WAS_ACTIVE" >"$BACKUP/previous.active"

SWITCH_STARTED=0
CHECKOUT_UPDATED=0
restore_application() {
    echo "Restoring the previous application and configuration. Backup: $BACKUP" >&2
    systemctl stop "$SERVICE" || true
    cp -a "$BACKUP/previous.nginx" "$SITE"
    cp -a "$BACKUP/previous.service" "$UNIT"
    if [[ -s $BACKUP/previous.release ]]; then
        ln -sfn "$(cat "$BACKUP/previous.release")" "$PROJECT/.deploy/current.rollback"
        mv -Tf "$PROJECT/.deploy/current.rollback" "$PROJECT/.deploy/current"
    fi
    if [[ $CHECKOUT_UPDATED == 1 ]]; then
        git -C "$PROJECT" reset --hard "$OLD_REVISION"
    fi
    systemctl daemon-reload
    nginx -t && systemctl reload nginx
    [[ $WAS_ACTIVE == 0 ]] || systemctl start "$SERVICE"
}
on_error() {
    local result=$?
    trap - ERR
    if [[ $SWITCH_STARTED == 1 ]]; then
        restore_application || true
    fi
    echo "Deployment failed. Database snapshot, configuration and commit records: $BACKUP" >&2
    echo 'Database migrations are retained. Use the documented offline restore only if database recovery is required.' >&2
    exit "$result"
}
trap on_error ERR

getent passwd mango-talk >/dev/null || useradd --system --user-group --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin mango-talk
install -d -o mango-talk -g mango-talk -m 0750 "$PROJECT/uploads" "$PROJECT/logs"
chown -R --no-dereference mango-talk:mango-talk "$PROJECT/uploads" "$PROJECT/logs"
chown root:mango-talk "$PROJECT/backend/.env"
chmod 640 "$PROJECT/backend/.env"
runuser -u mango-talk -- test -r "$PROJECT/backend/.env"
runuser -u mango-talk -- test -x "$RELEASE/backend/.venv/bin/python"

SWITCH_STARTED=1
systemctl stop "$SERVICE"
"$PYTHON" "$TOOLS/database_snapshot.py" backup --backend "$RELEASE/backend" --snapshot "$BACKUP/database.sql.gz"
(
    cd "$RELEASE/backend"
    "$PYTHON" -m app.db.migrate
)
ln -s "$RELEASE" "$PROJECT/.deploy/current.next"
mv -Tf "$PROJECT/.deploy/current.next" "$PROJECT/.deploy/current"
install -m 0644 "$BACKUP/next.service" "$UNIT"
install -m 0644 "$BACKUP/next.nginx" "$SITE"
nginx -t
systemctl daemon-reload
systemctl restart "$SERVICE"

wait_for_health() {
    for _ in {1..30}; do
        if curl -fsS --max-time 3 http://127.0.0.1:8000/health/db >/dev/null; then
            return 0
        fi
        sleep 1
    done
    return 1
}
wait_for_health
systemctl reload nginx
curl -fsS --max-time 10 https://mango-talk.chenglan.tech/health/db >/dev/null
curl -fsS --max-time 10 https://mango-talk.chenglan.tech/release.json | python3 -c 'import json,sys; assert json.load(sys.stdin)["commit"] == sys.argv[1]' "$REVISION"
curl -fsS --max-time 10 https://mango-talk.chenglan.tech/demo >/dev/null

git -C "$PROJECT" merge --ff-only "$REVISION"
CHECKOUT_UPDATED=1
systemctl enable "$SERVICE"
printf '%s\n' "$BACKUP" >"$PROJECT/.deploy/latest-backup"
trap - ERR
echo "Deployed $REVISION to https://mango-talk.chenglan.tech"
echo "Release: $RELEASE"
echo "Rollback checkpoint: $BACKUP"
