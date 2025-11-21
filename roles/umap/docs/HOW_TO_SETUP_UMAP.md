# How to Setup uMap

Diese Anleitung erklärt, wie ein uMap-Server mit diesem Ansible-Setup aufgesetzt wird. 

## Übersicht

## Voraussetzungen

### Systemanforderungen
- Debian 12 
- Root-Zugriff auf den Server
- Ansible >= 2.9 installiert
- SSH-Zugriff zum Server

### Server-Bootstrap
- Vor dem uMap-Setup muss der Server gebootstrappt werden
- DNS-Config und Domäns klären

### Ansible-Setup
1. Repository klonen
2. Ansible installieren 
   ```bash
   sudo apt install ansible
   ```

## Schritt 1: Host-Konfiguration

### 1.1 Host zum Inventory hinzufügen

Füge den neuen Host in `hosts.ini` hinzu:
```ini
[umap]
boggs ansible_host=boggs.openstreetmap.de
```


### 1.2 Host-Variablen erstellen

Erstelle `host_vars/<hostname>.yml` mit mindestens:
```yaml
umap__server_url: "umap.openstreetmap.de"

webserver__in_use: nginx
```

## Schritt 2: Erforderliche Variablen konfigurieren

Alle erforderlichen Variablen müssen in `private/vars/umap.yml` definiert werden.

### 2.1 OAuth2-Credentials für OpenStreetMap

uMap verwendet OAuth2 für die Authentifizierung über OpenStreetMap.

**Woher bekommt man die OAuth2-Keys?**

1. Gehe zu https://www.openstreetmap.org/user/<dein-username>/oauth_clients
2. Klicke auf "Register your application"
3. Fülle das Formular aus:
   - **Name**: z.B. "uMap Production"
   - **Redirect URIs**: `https://umap.openstreetmap.de/complete/openstreetmap-oauth2/`
   - **Permissions**: Wähle die benötigten Berechtigungen
4. Nach dem Erstellen erhältst du:
   - **Client ID** (Key)
   - **Client Secret** (Secret)

**In `private/vars/umap.yml` eintragen:**
```yaml
umap__social_auth_openstreetmap_oauth2_key: "DEIN_CLIENT_ID_HIER"
umap__social_auth_openstreetmap_oauth2_secret: "DEIN_CLIENT_SECRET_HIER"
```

### 2.2 Django Secret Key

Ein sicherer Secret Key für Django-Sessions und CSRF-Schutz.

**Generieren:**
```python
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

**In `private/vars/umap.yml` eintragen:**
```yaml
umap__django_secret_key: "DEIN_GENERIERTER_SECRET_KEY_HIER"
```

**Hinweis:** Das Secret wird auch zur Generierung der geheimen Bearbeitungslinks benutzt. Das heißt, wenn sich dieses Secret ändert, funktionieren zuvor erstellte Links nicht mehr. Soll eine bestehende uMap-Instanz auf einen neuen Server installiert werden, muss das alte Secret weiterverwendet werden. 

### 2.3 Datenbank-Passwort

Ein sicheres Passwort für die PostgreSQL-Datenbank.

**Generieren:**
```bash
openssl rand -base64 32
```

**In `private/vars/umap.yml` eintragen:**
```yaml
umap__database_password: "DEIN_DATENBANK_PASSWORT_HIER"
```

### 2.4 OpenRouteService API Key (optional)

Für Routing-Funktionalität in uMap.

**Woher bekommt man den API Key?**

1. Gehe zu https://account.heigit.org/signup
2. Registriere einen Account
3. Erstelle ein neues Projekt
4. Kopiere den API Key

**In `private/vars/umap.yml` eintragen:**
```yaml
umap__openrouteservice_apikey: "DEIN_ORS_API_KEY_HIER"
```
Wenn dieser API-Key nicht definiert ist, wird das zugehörige Feature in uMap nicht aktiviert. 


## Schritt 3: Optionale Backup-Konfiguration

### 3.1 Backup aktivieren

Falls Backups aktiviert werden sollen, füge in `host_vars/<hostname>.yml` hinzu:
```yaml
umap__backup_enabled: true
umap__backup_remote_user: "<storagebox-user>"
umap__backup_remote_host: "<storagebox-user>.your-storagebox.de"
umap__backup_remote_port: <port>
```

**Hinweis:** Für Backups wurde bisher https://www.hetzner.com/de/storage/storage-box/ benutzt. Frag das FOSSGIS-Admin-Team, wie man Zugang erhält.

### 3.2 SSH-Key für Backups

**Wenn Backups aktiviert sind, wird ein SSH-Key benötigt:**

Der SSH-Key wird **automatisch auf dem Server generiert** beim ersten Playbook-Lauf. Nach der Generierung muss der öffentliche Key manuell auf die Storage Box deployt werden.

**Workflow:**

1. **Playbook das erste Mal ausführen:**
   ```bash
   ansible-playbook -l <hostname> -i hosts.ini site.yml
   ```
   Das Playbook generiert automatisch einen SSH-Key auf dem Server unter `/srv/umap/.ssh/id_ed25519_borgbackup` und stoppt dann mit einer Anweisung.

2. **Öffentlichen Key auf Storage Box deployen:**
   
   **WICHTIG:** Das Deployment muss **VOM uMap-Server aus** erfolgen, nicht vom Ansible-Host!
   
   Deploye den öffentlichen Key auf die Storage Box mit deinem persönlichen SSH-Key (muss bereits auf der Storage Box hinterlegt sein):
   ```bash
   sudo -u umap cat /srv/umap/.ssh/id_ed25519_borgbackup.pub | ssh -p <port> <user>@<storagebox-host> install-ssh-key
   ```
   
   **Hinweis:** Der SSH-Key muss auf dem uMap-Server verfügbar sein. Falls der Key keinen Standard-Namen hat, verwende die Option `-i`:
   ```bash
   sudo -u umap cat /srv/umap/.ssh/id_ed25519_borgbackup.pub | ssh -i ~/.ssh/dein-key-name -p <port> <user>@<storagebox-host> install-ssh-key
   ```
   
3. **Playbook erneut ausführen:**
   ```bash
   ansible-playbook -l <hostname> -i hosts.ini site.yml
   ```
   Das Playbook testet nun die SSH-Verbindung und setzt das Setup fort.

**Hinweis:** Für Zugriff auf einen bestehenden Backup-Server frage das FOSSGIS-Admin-Team.

### 3.3 BorgBackup Passphrase

**In `private/vars/umap.yml` eintragen:**
```yaml
umap__backup_passphrase: "DEIN_SICHERES_PASSPHRASE_HIER"
```

**WICHTIG:** Diese Passphrase wird für die Verschlüsselung der Backups verwendet. Ohne diese Passphrase können Backups nicht wiederhergestellt werden.



### 3.4 Backup-Verzeichnisstruktur auf StorageBox

Die StorageBox muss folgende Verzeichnisstruktur haben:
```
/backups/
  └── <hostname>/
      ├── umapdata/    # Data-Backups (Dateien, Medien)
      └── umapdb/      # DB-Backups (Datenbank-Dumps)
```

Diese Verzeichnisse werden beim ersten Backup automatisch erstellt (Borg init).



## Schritt 4: Deployment ausführen

### 4.1 Vollständiges Deployment

Führe das Haupt-Playbook aus:
```bash
ansible-playbook -l <hostname> -i hosts.ini site.yml
```


### 4.2 Was wird installiert?

Das Playbook führt folgende Schritte aus:

1. **System-Setup:**
   - Erstellt `umap` Benutzer
   - Installiert Docker und Docker Compose
   - Richtet Verzeichnisstruktur ein

2. **uMap-Container:**
   - PostgreSQL/PostGIS Datenbank-Container
   - uMap-Anwendungs-Container
   - Nginx-Container
   - Redis-Container

3. **Konfiguration:**
   - Django-Konfiguration (`umap.conf`)
   - Datenbank-Umgebungsvariablen
   - Nginx-Konfiguration
   - SSL-Zertifikate (Let's Encrypt)
   - Scripte für uMap Administration und Backup
   - Custom Templates für FOSSGIS-Fußzeile

4. **Backups:** 
   - Installiert BorgBackup
   - Generiert SSH-Key automatisch auf dem Server
   - Erstellt SSH-Konfiguration
   - Initialisiert Borg-Repositories
   - Richtet systemd-Timer für automatische Backups ein

5. **Monitoring:**
   - Munin-Plugins für Statistiken



## Schritt 5: Verifizierung

### 5.1 Service-Status prüfen

```bash
docker container ps
```
Alle Container sollten laufen:
- `umap_app`
- `umap_db`
- `umap_nginx`
- `umap_redis`

Host-Nginx prüfen
```bash
systemctl status nginx.service

```


### 5.2 Backup-Status prüfen (wenn aktiviert)

Systemd-Dienste prüfen

```bash
sudo systemctl status borgbackup-data.service
sudo systemctl status borgbackup-db.service
```

```bash
ssh <hostname>
sudo /srv/umap/scripts/admin/umap-backup.sh list
sudo /srv/umap/scripts/admin/umap-backup.sh info
```

### 5.3 Wichtige Logs

Für die Fehlersuche und Überwachung sind folgende Logs wichtig:

#### Nginx Logs (Dateien)

Die Nginx-Logs werden im Container geschrieben und auf den Host gemountet:

```bash
tail -f /srv/umap/nginx/logs/access.log
tail -f /srv/umap/nginx/logs/error.log
```

**Hinweis:** Die Logs werden täglich rotiert (14 Tage Aufbewahrung) via logrotate.

#### Systemd Service Logs (Backups)

**Backup-Services:**
```bash
# Status und letzte Logs
sudo journalctl -u borgbackup-db.service
sudo journalctl -u borgbackup-data.service

```

**Alle Backup-Logs zusammen:**
```bash
sudo journalctl -u borgbackup-db.service -u borgbackup-data.service
```

#### Host-Nginx Logs

```bash
# Access Log
sudo tail -f /var/log/nginx/umapde-access.log

# Error Log
sudo tail -f /var/log/nginx/umapde-error.log

# Alle Nginx-Logs
sudo journalctl -u nginx.service -f
```

#### Docker System Logs

```bash
# Docker-Daemon Logs
sudo journalctl -u docker.service -f

docker compose -f /srv/umap/docker-compose.yml logs [container name]
```



## Schritt 6: Admin-Zugang einrichten

### 6.1 Superuser erstellen (falls kein Restore geplant ist)

```bash
ssh <hostname>
sudo -u umap docker exec umap_app python manage.py createsuperuser
```

Folge den Anweisungen zur Eingabe von Benutzername, E-Mail und Passwort.

### 6.2 Admin-Interface

Zugriff auf das Django-Admin-Interface:
```
https://umap.openstreetmap.de/admin/
```


## Weitere Dokumentation

- Backup-Verwaltung: `roles/umap/docs/README_BACKUP.md`
- Admin-Skripte: `roles/umap/docs/README_ADMINSCRIPTS.md`
- Verzeichnisstruktur: `roles/umap/docs/DIRECTORY_TREE.md`

