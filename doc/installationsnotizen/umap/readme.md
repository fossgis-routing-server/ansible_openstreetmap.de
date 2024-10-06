uMap Server

Das Setup besteht aus

- Traefik: als Webserverersatz, Letsencrypt-Zertifikate werden automatisch erzeugt und aktualisiert
- Docker: Container für PostgreSQL, uMap, traefik 
- uMap: uMap-Application

Starten der Container
cd /srv/umap/deploy/umap
docker compose up -d

cd /srv/umap/deploy/reverseproxy
docker compose up -d 
