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
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

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
        RELEASE_TAG=$(python3 -c "\
            import urllib.request, json; \
            response = urllib.request.urlopen('https://api.github.com/repos/umap-project/umap/releases/latest'); \
            data = json.loads(response.read()); \
            print(data['tag_name'])\
        "); \
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
        git clone --branch $RELEASE_TAG --depth 1 https://github.com/umap-project/umap.git /tmp/umap; \
    fi && \
    cp -r /tmp/umap/* /srv/umap/ && \
    rm -rf /tmp/umap

# Install original uMap dependencies
RUN /venv/bin/pip install .[docker,s3,sync]

RUN /venv/bin/pip install uvicorn[standard] channels

# Copy entrypoint script
COPY entrypoint.sh /srv/umap/docker/entrypoint.sh
RUN chmod +x /srv/umap/docker/entrypoint.sh

FROM common

COPY --from=build /srv/umap/docker/ /srv/umap/docker/
COPY --from=build /venv/ /venv/

WORKDIR /srv/umap

RUN mkdir -p /srv/umap/media_root /srv/umap/cache

ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PATH="/venv/bin:$PATH"

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["/srv/umap/docker/entrypoint.sh"]
