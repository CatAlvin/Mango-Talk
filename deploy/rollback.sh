#!/usr/bin/env bash
# Restore an application checkpoint. Schema changes and new messages are retained.
set -Eeuo pipefail
BACKUP=$(realpath "${1:?Usage: rollback.sh PROJECT/.deploy/backups/CHECKPOINT}")
PROJECT=$(dirname "$(dirname "$(dirname "$BACKUP")")")
[[ $EUID == 0 && $BACKUP == "$PROJECT/.deploy/backups/"* && -d $BACKUP ]] || exit 1
[[ $PROJECT =~ ^/[a-zA-Z0-9._/-]+/mango-talk$ && $PROJECT != *..* ]] || exit 1
for file in previous.commit release.commit previous.service previous.nginx previous.active; do
    [[ -f $BACKUP/$file ]] || { echo "Incomplete checkpoint: $file" >&2; exit 1; }
done
exec 9>"$PROJECT/.deploy/deployment.lock"
flock -n 9 || { echo 'Another Mango Talk deployment is running.' >&2; exit 1; }
[[ -z $(git -C "$PROJECT" status --porcelain -- . ':(exclude).deploy') ]] || { echo 'The checkout has local changes; rollback stopped.' >&2; exit 1; }
[[ $(git -C "$PROJECT" rev-parse HEAD) == "$(cat "$BACKUP/release.commit")" ]] || { echo 'The checkpoint does not match the deployed checkout.' >&2; exit 1; }
systemctl stop mango-talk-api.service
cp -a "$BACKUP/previous.service" /etc/systemd/system/mango-talk-api.service
cp -a "$BACKUP/previous.nginx" /etc/nginx/sites-available/mango-talk
if [[ -s $BACKUP/previous.release ]]; then
    PREVIOUS=$(cat "$BACKUP/previous.release")
    [[ $PREVIOUS == "$PROJECT/.deploy/releases/"* && -d $PREVIOUS ]] || { echo 'The previous release is missing; keep the API stopped.' >&2; exit 1; }
    ln -sfn "$PREVIOUS" "$PROJECT/.deploy/current.rollback"
    mv -Tf "$PROJECT/.deploy/current.rollback" "$PROJECT/.deploy/current"
fi
git -C "$PROJECT" reset --hard "$(cat "$BACKUP/previous.commit")"
systemctl daemon-reload
nginx -t
systemctl reload nginx
[[ $(cat "$BACKUP/previous.active") == 0 ]] || systemctl start mango-talk-api.service
curl -fsS --retry 5 --retry-connrefused --retry-delay 1 --max-time 5 http://127.0.0.1:8000/health/db >/dev/null
echo "Application rollback completed. Database contents and additive migrations were retained. Checkpoint: $BACKUP"
