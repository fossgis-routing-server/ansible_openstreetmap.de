# uMap Backup System

Dieses Dokument beschreibt das Backup-System für uMap, das Borg Backup verwendet und automatisch per Ansible deployt wird.

## Übersicht

Das Backup-System besteht aus:
- **SSH-Keys**: Unique pro Server für sichere Verbindung zur StorageBox (`/srv/umap/.ssh/`)
- **Borg-Passphrase**: Gleiche für alle Server zur Entschlüsselung der Backup-Daten
- **Backup-Scripts**: Automatische DB- und Daten-Backups (deployt nach `/srv/umap/scripts/backup/`)
- **Systemd Timer**: Tägliche Ausführung der Backups
- **Backup-Management-Tool**: `/srv/umap/scripts/admin/umap-backup.sh` für manuelle Operationen

## Konfiguration

### SSH-Key bereitstellen

Ohne SSH-Key funktioniert kein Backup! Die Backup-Scripts prüfen beim Start, ob der SSH-Key existiert und beenden sich mit einem Fehler, wenn der Key fehlt.

Der SSH-Key muss in das `sshkeys/` Verzeichnis im Playbook-Verzeichnis gelegt werden.
Ansible kopiert den Key beim nächsten Deployment automatisch auf den Server und setzt die korrekten Berechtigungen:
- Owner: `umap`
- Group: `borgbackup`
- Berechtigungen: `0600` (rw-------)

Ansible kopiert den SSH-Key nur, wenn auf dem Server noch kein Key mit diesem Namen existiert. Falls bereits ein Key vorhanden ist, muss dieser manuell gelöscht werden, bevor Ansible den neuen Key deployen kann. Ansible setzt beim nächsten Deployment automatisch die korrekten Berechtigungen, wie oben erwähnt.


### Borg-Passphrase konfigurieren

Ohne Passphrase werden die Backups nicht verschlüsselt! 

```yaml
# In private/vars/umap.yml
umap__backup_passphrase: "MeineSicherePassphrase"
```

### Backup-Konfiguration

**`group_vars/umap.yml`**:
```yaml
umap__backup_ssh_key_name: "id_ed25519_borgbackup"
umap__backup_passphrase: "{{ umap__backup_passphrase }}"
umap__backup_remote_port: "{{ umap__backup_remote_port | default(22) }}"
umap__backup_keep_daily: 7
umap__backup_keep_weekly: 4
umap__backup_keep_monthly: 3
```

In host_vars werden die Verbindungsparameter hinterlegt.
**`host_vars/<hostname>.yml`** (host-spezifisch):
```yaml
umap__backup_enabled: true
umap__backup_remote_user: "u426902"
umap__backup_remote_host: "u426902.your-storagebox.de"
umap__backup_remote_port: 23
```

Die Variable `umap__backup_enabled` muss pro Host in `host_vars/<hostname>.yml` gesetzt werden, um Backups für diesen Host zu aktivieren. Der Name des SSH-Keys muss mit dem tatsächlichen Namen der SSH-Key-Datei übereinstimmen.

### Retention-Policy

Die Retention-Policy bestimmt, wie lange Backups aufbewahrt werden. Die Standard-Konfiguration behält:
- **7 tägliche Backups**: Die letzten 7 Tage werden vollständig gesichert
- **4 wöchentliche Backups**: Zusätzlich werden 4 wöchentliche Backups (jeweils das neueste Backup der Woche) aufbewahrt
- **3 monatliche Backups**: Zusätzlich werden 3 monatliche Backups (jeweils das neueste Backup des Monats) aufbewahrt

Pro Tag wird nur das neueste Backup aufbewahrt. Wenn mehrere Backups am selben Tag erstellt werden (z.B. durch manuelle Ausführung), wird nur das neueste Backup behalten und die älteren Backups des Tages werden automatisch gelöscht.

Die Retention-Policy wird automatisch bei jedem Backup ausgeführt (`borg prune`), sodass alte Backups automatisch gelöscht werden, wenn sie außerhalb der Retention-Policy liegen.

### Backup-Server Verzeichnisstruktur

Die Backups werden auf dem Backup-Server in folgender Struktur gespeichert:

```
./backups/<hostname>/umapdata/    # Daten-Backups
./backups/<hostname>/umapdb/      # Datenbank-Backups
```

Wenn mehrere Server Backups auf denselben Backup-Server schreiben, muss sichergestellt werden, dass die Verzeichnisstruktur kompatibel ist. Jeder Server verwendet seinen Hostnamen (`inventory_hostname`) als Verzeichnisname, daher sollten Hostnamen eindeutig sein.

## Backup erstellen

### Automatisch

Backups laufen täglich um 02:00 Uhr automatisch via Systemd Timer:

```bash
# Timer-Status prüfen
sudo systemctl status borgbackup-db.timer
sudo systemctl status borgbackup-data.timer

# Nächste Ausführung anzeigen
systemctl list-timers borgbackup-*.timer
```

### Manuell

#### Mit Backup-Management-Tool
```bash
# Database Backup starten
sudo /srv/umap/scripts/admin/umap-backup.sh backup umapdb

# Data Backup starten
sudo /srv/umap/scripts/admin/umap-backup.sh backup umapdata

# Beide Backups starten
sudo /srv/umap/scripts/admin/umap-backup.sh backup all
```
Es sollte darauf geachtet werden, die DB und die Daten zum gleichen Zeitpunkt zu sichern. 


#### Mit Systemd Service
```bash
# Database Backup starten
sudo systemctl start borgbackup-db.service

# Data Backup starten
sudo systemctl start borgbackup-data.service

# Logs verfolgen
sudo journalctl -u borgbackup-db.service -f
```


### Backup-Status prüfen

```bash
# Backups auflisten
sudo /srv/umap/scripts/admin/umap-backup.sh list

# Repository-Informationen
sudo /srv/umap/scripts/admin/umap-backup.sh info

# Verbindung testen
sudo /srv/umap/scripts/admin/umap-backup.sh test
```

## Wiederherstellung

### Vorbereitung: Halb-Restore

Backups können vom Remote-Server extrahiert und in ein lokales Verzeichnis kopiert werden, ohne sie direkt in die Produktionsverzeichnisse wiederherzustellen. Da die Übertragung vom Backupserver für ca. 180 GB Daten ungefähr eine Stunde dauert, ist es besser, zuerst in ein lokales Verzeichnis zu extrahieren. Im nächsten Schritt erst werden die Daten in das richtige Verzeichnis verschoben bzw. das DB-Backup importiert.

```bash
# Backups auflisten
sudo /srv/umap/scripts/admin/umap-backup.sh list

# Neueste Backups holen (Standard-Verzeichnis: /srv/umap/restoredata/)
sudo /srv/umap/scripts/admin/umap-backup.sh restore-prepare

# Bestimmtes Archiv holen
sudo /srv/umap/scripts/admin/umap-backup.sh restore-prepare umapdb-202510291955 umapdata-202510141200

# Alternatives Verzeichnis verwenden
sudo /srv/umap/scripts/admin/umap-backup.sh restore-prepare --restore-dir /tmp/my-restore
```

Die extrahierten Backups werden standardmäßig nach `/srv/umap/restoredata/` kopiert (oder in das mit `--restore-dir` angegebene Verzeichnis):
- `/srv/umap/restoredata/<timestamp>/umapdb/` - DB-Backup als SQL-Datei
- `/srv/umap/restoredata/<timestamp>/umapdata/` - Extrahiertes Data-Backup

Mit dem Parameter `--restore-dir` (oder `-d`) kann ein alternatives Verzeichnis angegeben werden. Wenn der Parameter nicht angegeben wird, wird das Standard-Verzeichnis `/srv/umap/restoredata/` verwendet.

### Vollständiger Restore

Nach dem Halb-Restore kann ein vollständiger Restore durchgeführt werden:

#### Database wiederherstellen

**Mit Backup-Management-Tool**:
```bash
# SQL-Datei ist optional - wenn nicht angegeben, wird die neueste verwendet
sudo /srv/umap/scripts/admin/umap-backup.sh restore umapdb

# Oder spezifische SQL-Datei angeben (Dateiname oder vollständiger Pfad)
sudo /srv/umap/scripts/admin/umap-backup.sh restore umapdb umapdb-202510291955.sql
sudo /srv/umap/scripts/admin/umap-backup.sh restore umapdb /srv/umap/restoredata/umapdb/umapdb-202510291955.sql
```

**Hinweis:** 
- Wenn keine SQL-Datei angegeben wird, verwendet das Tool automatisch die neueste SQL-Datei aus dem Restore-Verzeichnis (Standard: `/srv/umap/restoredata/`).
- Wenn nur ein Dateiname angegeben wird (ohne Pfad), sucht das Tool im Standard-Verzeichnis `/srv/umap/restoredata/`.
- Wenn ein vollständiger Pfad angegeben wird, wird dieser direkt verwendet.
- Mit `--restore-dir` kann ein alternatives Verzeichnis angegeben werden, aus dem die Backups wiederhergestellt werden sollen. Wichtig ist, dass `--restore-dir` dann immer angegeben werden muss.

Das Tool führt automatisch folgende Schritte aus:
1. Stoppt alle Docker-Container
2. Entfernt alle Container
3. Löscht alle Volumes (umap_db_data, umap_cache_data, umap_redis_data)
4. Startet nur den DB-Container
5. Kopiert die SQL-Datei in den DB-Container
6. Spielt die SQL-Datei in die Datenbank ein



#### Daten wiederherstellen

**Mit Backup-Management-Tool**:
```bash
# Standard-Verzeichnis verwenden (/srv/umap/restoredata/)
sudo /srv/umap/scripts/admin/umap-backup.sh restore umapdata

# Alternatives Restore-Verzeichnis verwenden
sudo /srv/umap/scripts/admin/umap-backup.sh restore --restore-dir /tmp/my-restore umapdata
```

Das Tool führt automatisch folgende Schritte aus:
1. Löscht den gesamten Inhalt von `/srv/umap/umapdata/`
2. Verschiebt alle Dateien aus dem Restore-Verzeichnis (Standard: `/srv/umap/restoredata/<timestamp>/umapdata/`) nach `/srv/umap/umapdata/`
3. Setzt die korrekten Berechtigungen (umap:docker)


## Backup-Management-Tool

Das Tool `/srv/umap/scripts/admin/umap-backup.sh` bietet folgende Funktionen:

```bash
# Alle Hosts auf dem Backup-Server auflisten
sudo /srv/umap/scripts/admin/umap-backup.sh list-hosts

# Backups auflisten
sudo /srv/umap/scripts/admin/umap-backup.sh list [--host <hostname>] [umapdata|umapdb]
# Beispiele:
#   sudo /srv/umap/scripts/admin/umap-backup.sh list                           # Backups des aktuellen Hosts
#   sudo /srv/umap/scripts/admin/umap-backup.sh list --host <hostname>         # Backups von anderem Host
#   sudo /srv/umap/scripts/admin/umap-backup.sh list --host <hostname> umapdb  # Nur DB-Backups von anderem Host

# Repository-Informationen
sudo /srv/umap/scripts/admin/umap-backup.sh info [--host <hostname>] [umapdata|umapdb]
# Beispiele:
#   sudo /srv/umap/scripts/admin/umap-backup.sh info                           # Info des aktuellen Hosts
#   sudo /srv/umap/scripts/admin/umap-backup.sh info --host <hostname>         # Info von anderem Host
#   sudo /srv/umap/scripts/admin/umap-backup.sh info --host <hostname> umapdb  # Nur DB-Info von anderem Host

# Verbindung testen
sudo /srv/umap/scripts/admin/umap-backup.sh test [umapdata|umapdb]

# Manuelles Backup starten
sudo /srv/umap/scripts/admin/umap-backup.sh backup umapdata|umapdb|all

# Halb-Restore: Backups in lokales Verzeichnis kopieren
sudo /srv/umap/scripts/admin/umap-backup.sh restore-prepare [--restore-dir <dir>] [--host <hostname>] [umapdb|umapdata] [umapdb-ARCHIV] [umapdata-ARCHIV]
# Beispiele:
#   sudo /srv/umap/scripts/admin/umap-backup.sh restore-prepare                                    # Neueste Backups in Standard-Verzeichnis (/srv/umap/restoredata/)
#   sudo /srv/umap/scripts/admin/umap-backup.sh restore-prepare --restore-dir /tmp/my-restore      # Neueste Backups in alternatives Verzeichnis
#   sudo /srv/umap/scripts/admin/umap-backup.sh restore-prepare --host <hostname> umapdb           # Nur DB-Backup von anderem Host
#   sudo /srv/umap/scripts/admin/umap-backup.sh restore-prepare --host <hostname> umapdata         # Nur Data-Backup von anderem Host
#   sudo /srv/umap/scripts/admin/umap-backup.sh restore-prepare --restore-dir /tmp/my-restore --host <hostname>  # Kombination beider Parameter

# Vollständiger Restore
sudo /srv/umap/scripts/admin/umap-backup.sh restore [--restore-dir <dir>] umapdb [sql-file]    # Nur DB (sql-file optional: Dateiname oder Pfad)
sudo /srv/umap/scripts/admin/umap-backup.sh restore [--restore-dir <dir>] umapdata             # Nur Daten
sudo /srv/umap/scripts/admin/umap-backup.sh restore [--restore-dir <dir>] all                   # DB + Daten
# Beispiele:
#   sudo /srv/umap/scripts/admin/umap-backup.sh restore umapdb                                    # DB-Restore mit neuester SQL-Datei (aus Standard-Verzeichnis)
#   sudo /srv/umap/scripts/admin/umap-backup.sh restore umapdb umapdb-202510291955.sql           # DB-Restore mit Dateiname (aus Standard-Verzeichnis)
#   sudo /srv/umap/scripts/admin/umap-backup.sh restore umapdb /path/to/file.sql                  # DB-Restore mit vollständigem Pfad
#   sudo /srv/umap/scripts/admin/umap-backup.sh restore --restore-dir /tmp/my-restore umapdb      # DB-Restore aus alternatives Verzeichnis
#   sudo /srv/umap/scripts/admin/umap-backup.sh restore --restore-dir /tmp/my-restore all         # Vollständiger Restore aus alternatives Verzeichnis
```

### Serverumzug: Backup von anderem Host wiederherstellen

Bei einem Serverumzug können Backups von einem anderen Host wiederhergestellt werden:

```bash
# 1. Zeige alle verfügbaren Hosts auf dem Backup-Server
sudo /srv/umap/scripts/admin/umap-backup.sh list-hosts

# 2. Hole neueste Backups von einem anderen Host
sudo /srv/umap/scripts/admin/umap-backup.sh restore-prepare --host <hostname>

# 3. Oder hole spezifische Archive von einem anderen Host
sudo /srv/umap/scripts/admin/umap-backup.sh restore-prepare --host <hostname> umapdb-202510291955 umapdata-202510141200

# 3b. Oder verwende ein alternatives Verzeichnis für die Restore-Daten
sudo /srv/umap/scripts/admin/umap-backup.sh restore-prepare --restore-dir /tmp/my-restore --host <hostname>

# 4. Wiederherstellen (aus Standard-Verzeichnis)
sudo /srv/umap/scripts/admin/umap-backup.sh restore umapdb umapdb-202510291955.sql
sudo /srv/umap/scripts/admin/umap-backup.sh restore umapdata
# oder
sudo /srv/umap/scripts/admin/umap-backup.sh restore all

# 4b. Oder wiederherstellen aus alternatives Verzeichnis
sudo /srv/umap/scripts/admin/umap-backup.sh restore --restore-dir /tmp/my-restore all
```


## Troubleshooting

```bash
# Logs prüfen
sudo journalctl -u borgbackup-data.service -n 100
sudo journalctl -u borgbackup-db.service -n 100

# Verbindung testen
sudo /srv/umap/scripts/admin/umap-backup.sh test
```

