#!/bin/sh
set -eu

SITE_DIR="${SARDINE_PROJECT_DIR:-/site}"
DATA_DIR="$(dirname "${SARDINE_STORAGE_URL#sqlite:///}")"
mkdir -p "$DATA_DIR" "$SITE_DIR" "${SARDINE_MEDIA_DIR:-/data/media}"

# Scaffold a project on first run so the panel has something to serve.
if [ ! -f "$SITE_DIR/sardine.toml" ]; then
    echo "==> initializing example site"
    cms init "$SITE_DIR" \
        --name "Sardine CMS" \
        --base-url "http://localhost:8000" \
        --languages "pt-pt,es,fr,de" \
        --theme ph7x-reference
fi

# Seed starter content if the database is empty.
cms seed -p "$SITE_DIR" --force 2>/dev/null || true

# Create a default admin user on first run (password must be >= 12 chars).
ADMIN_PASSWORD="${SARDINE_ADMIN_PASSWORD:-sardine-admin-123}"
if ! cms admin create-user admin -p "$SITE_DIR" --role admin --password "$ADMIN_PASSWORD" 2>/dev/null; then
    echo "==> admin user already exists (or creation skipped)"
fi

echo "==> starting admin panel on :8000"
exec uvicorn --factory cms_admin.app:create_app --host 0.0.0.0 --port 8000
