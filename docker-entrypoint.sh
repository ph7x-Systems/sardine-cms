#!/bin/sh
set -eu

SITE_DIR="${SARDINE_PROJECT_DIR:-/site}"
DATA_DIR="$(dirname "${SARDINE_STORAGE_URL#sqlite:////}")"
mkdir -p "$DATA_DIR" "$SITE_DIR" "${SARDINE_MEDIA_DIR:-/data/media}"

# First-run setup: scaffold, seed, and create admin user.
if [ ! -f "$SITE_DIR/sardine.toml" ]; then
    echo "==> initializing example site"
    cms init "$SITE_DIR" \
        --name "Sardine CMS" \
        --base-url "http://localhost:8000" \
        --languages "pt-pt,es,fr,de" \
        --theme ph7x-reference

    echo "==> seeding starter content"
    cms seed -p "$SITE_DIR"

    # Generate a random password on first run if none is provided.
    if [ -z "${SARDINE_ADMIN_PASSWORD:-}" ]; then
        ADMIN_PASSWORD=$(head -c 16 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24)
        echo "==> generated admin password (save this — it won't be shown again):"
        echo "    admin / $ADMIN_PASSWORD"
    else
        ADMIN_PASSWORD="$SARDINE_ADMIN_PASSWORD"
        echo "==> admin user created from SARDINE_ADMIN_PASSWORD"
    fi
    cms admin create-user admin -p "$SITE_DIR" --role admin --password "$ADMIN_PASSWORD"
fi

echo "==> starting admin panel on :8000"
exec uvicorn --factory cms_admin.app:create_app --host 0.0.0.0 --port 8000
