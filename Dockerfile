FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SARDINE_STORAGE_URL=sqlite:///data/content.db \
    SARDINE_PROJECT_DIR=/site \
    SARDINE_MEDIA_DIR=/data/media \
    SARDINE_ADMIN_COOKIE_SECURE=0

WORKDIR /site

RUN pip install --no-cache-dir \
    sardine-cms-cli \
    sardine-cms-theme-ph7x-reference \
    sardine-cms-admin

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
