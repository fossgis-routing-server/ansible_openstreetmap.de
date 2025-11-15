# This part installs deps needed at runtime.
FROM python:3.12-slim AS common

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tini \
        sqlite3 \
        libpq-dev \
        gdal-bin \
        && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    rm -rf /root/.cache

# This part adds deps needed only at buildtime.
FROM common AS build

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        binutils \
        libproj-dev \
        curl \
        git \
        gettext \
        python3-venv \
        libffi-dev \
        libtiff5-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        libfreetype6-dev \
        liblcms2-dev \
        libwebp-dev

RUN python -m venv /venv

WORKDIR /srv/umap

# Build argument for uMap version (Default: release = latest stable version)
ARG UMAP_VERSION=release

# Download uMap from GitHub
RUN if [ "$UMAP_VERSION" = "release" ]; then \
        echo "Fetching latest stable release..."; \
        RELEASE_TAG=$(python3 -c "import urllib.request, json; response = urllib.request.urlopen('https://api.github.com/repos/umap-project/umap/releases/latest'); data = json.loads(response.read()); print(data['tag_name'])"); \
    elif [ "$UMAP_VERSION" = "main" ] || [ "$UMAP_VERSION" = "dev" ]; then \
        echo "Using development version from main branch"; \
        RELEASE_TAG=""; \
    else \
        echo "Using specified version: $UMAP_VERSION"; \
        RELEASE_TAG="$UMAP_VERSION"; \
    fi && \
    if [ -z "$RELEASE_TAG" ]; then \
        echo "Installing from main branch (development version)"; \
        git clone --depth 1 https://github.com/umap-project/umap.git /tmp/umap; \
    else \
        echo "Installing uMap release: $RELEASE_TAG"; \
        git clone --depth 1 https://github.com/umap-project/umap.git /tmp/umap; \
        cd /tmp/umap && git fetch --depth 1 origin tag $RELEASE_TAG && git checkout $RELEASE_TAG; \
    fi && \
    cp -r /tmp/umap/* /srv/umap/ && \
    rm -rf /tmp/umap

# Install original uMap dependencies
# sync extra is required for WebSocket/realtime features (REALTIME_ENABLED=True)
#   - sync: redis, websockets, pydantic for WebSocket/realtime features
# Optional extras (not currently used):
#   - docker: uvicorn (already installed separately, redundant)
#   - s3: django-storages[s3] for AWS S3 storage backend
# To enable s3: change .[sync] to .[sync,s3]
RUN /venv/bin/pip install --no-cache-dir .[sync] && \
    /venv/bin/pip install --no-cache-dir uvicorn[standard] channels && \
    rm -rf /tmp/* /root/.cache

# Copy entrypoint script
COPY entrypoint.sh /srv/umap/docker/entrypoint.sh
RUN chmod +x /srv/umap/docker/entrypoint.sh

FROM common

# Create umap user with configurable UID/GID to match host user
# UMAP_GID should match the host's docker group GID (group name in container doesn't matter)
ARG UMAP_UID=999
ARG UMAP_GID=988
RUN groupadd -g ${UMAP_GID} umap 2>/dev/null || true && \
    (useradd -u ${UMAP_UID} -g ${UMAP_GID} -d /srv/umap -s /bin/bash -m umap 2>/dev/null || \
     usermod -u ${UMAP_UID} -g ${UMAP_GID} umap) && \
    echo "umap:x:${UMAP_UID}:${UMAP_GID}:uMap User:/srv/umap:/bin/bash" >> /etc/passwd 2>/dev/null || true

COPY --from=build --chown=umap:umap /srv/umap/docker/ /srv/umap/docker/
COPY --from=build --chown=umap:umap /venv/ /venv/

WORKDIR /srv/umap

RUN mkdir -p /srv/umap/media_root /srv/umap/cache && \
    chown -R umap:umap /srv/umap

ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PATH="/venv/bin:$PATH"

EXPOSE 8000

USER umap

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["/srv/umap/docker/entrypoint.sh"]
