# uMap Admin-Skripte

Python-Skripte für Datenbank-Analyse und Verwaltung.

## Skripte

- `umap-admin` - Wrapper-Script für alle Python-Admin-Skripte
- `analyze_users.py` - User-Analyse nach Karten, Layern, Teams, Datenvolumen
- `analyze_maps.py` - Karten-Analyse nach Größe, Aktivität, Layer-Anzahl
- `get_map_details.py` - Karten-Details mit Layer-Informationen und GeoJSON-Pfaden
- `get_user_details.py` - Detaillierte User-Informationen
- `umap-backup.sh` - Backup-Management-Tool
  - Siehe `README_BACKUP.md` für detaillierte Dokumentation

## Verwendung

### Wrapper-Skript `umap-admin`

```bash
cd /srv/umap/scripts/admin

./umap-admin help
./umap-admin analyze users [OPTIONS]
./umap-admin analyze maps [OPTIONS]
./umap-admin get map <id>|<url>
./umap-admin get user <id>|<username>
```

### Ausführung direkt auf dem Host

Das Wrapper-Script kann direkt auf dem Host ausgeführt werden, nicht im Docker Container:

```bash
/srv/umap/scripts/admin/umap-admin get user <USER_ID>
```

## Detaillierte Skript-Beschreibungen

### analyze_users.py

Analysiert User nach Karten, Layern, Teams und Datenvolumen.

**Aufruf:**
```bash
./umap-admin analyze users [--top N] [--sort SORT]
```

**Sortieroptionen:** `maps`, `layers`, `size`, `teams`, `username`

**Ausgabe:** Tabellarische Übersicht der Top-User mit Statistiken

---

### analyze_maps.py

Analysiert Karten nach Größe, Aktivität und anderen Metriken.

**Aufruf:**
```bash
./umap-admin analyze maps [--top N] [--metric METRIC]
```

**Metriken:**
- `size` - Nach Gesamtgröße (Standard)
- `layers` - Nach Layer-Anzahl
- `activity` - Nach Aktivität
- `inactive` - Inaktive Karten
- `largest-layers` - Größte einzelne Layer

**Ausgabe:** Tabellarische Übersicht der analysierten Karten/Layer

---

### get_map_details.py

Zeigt alle Layer einer Karte mit GeoJSON-Dateipfaden und Details.

**Aufruf:**
```bash
./umap-admin get map <map_id>|<url>
```

**Funktionen:**
- Zeigt Layer mit UUID, Name, GeoJSON-Pfad, Größe, Rank, Timestamps
- Zeigt Map-Informationen (Name, Slug, Owner, Erstellungs-/Änderungsdatum)
- Zeigt weitere Maps des gleichen Users

**Ausgabe:** Detaillierte Liste aller Layer mit vollständigen Pfaden (Container- und Host-Pfade)

---

### get_user_details.py

Zeigt detaillierte Informationen zu einem User.

**Aufruf:**
```bash
./umap-admin get user <user_id>|<username>
```

**Funktionen:**
- Sucht User nach ID oder Username
- Zeigt Statistiken: eigene Karten, Editor-Karten, Teams, Gesamtgröße
- Zeigt alle eigenen Karten mit Details (Größe, Layer-Anzahl, Share-Status)
- Top 5 größte Karten

**Ausgabe:** Detaillierte User-Übersicht mit allen Statistiken

---

## Beispiele

```bash
./umap-admin analyze users --top 50 --sort size
./umap-admin analyze maps --metric activity --top 30
./umap-admin get map <MAP_ID>
./umap-admin get map https://umap.example.com/de/map/karte_<MAP_ID>/
./umap-admin get user <USER_ID>
```

## Technische Details

### Gemeinsames Utility-Modul: umap_utils.py

Alle Skripte nutzen `umap_utils.py` für:

**Django-Setup:**
- `setup_django()` - Initialisiert Django und stellt die Datenbankverbindung her
- `load_database_env()` - Lädt Umgebungsvariablen aus `database.env` (automatisch)

**Pfad-Ermittlung (robust mit Fallbacks):**
- `get_umap_basedir()` - Ermittelt das uMap Base-Verzeichnis
- `get_media_root()` - Ermittelt den MEDIA_ROOT-Pfad
- `get_umap_settings_path()` - Ermittelt den Pfad zur uMap-Konfigurationsdatei
- `get_script_dir()` - Ermittelt das Script-Verzeichnis

**Container-Erkennung:**
- `is_in_container()` - Prüft ob das Script im Docker-Container läuft

**Formatierung:**
- `format_size()` - Formatiert Bytes in lesbare Größe (B, KB, MB, GB, TB)
- `format_date()` - Formatiert Datum kompakt (mit optionaler Zeit)
- `format_days_ago()` - Berechnet Tage seit Datum
- `format_share_status()` - Formatiert Share-Status als "ö" (öffentlich) oder "p" (privat)

**Datei-Operationen:**
- `get_layer_file_size()` - Ermittelt die Dateigröße eines Layers (mit Fallback-Suche)


### Umgebungsvariablen

**Datenbankverbindung (aus `database.env`):**
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`

**uMap-Konfiguration (optional, automatisch erkannt):**
- `UMAP_BASEDIR` - uMap Base-Verzeichnis (Standard: automatisch erkannt)
- `UMAP_MEDIA_ROOT` - MEDIA_ROOT-Pfad (Standard: automatisch erkannt)
- `UMAP_SETTINGS` - Pfad zur uMap-Konfigurationsdatei (Standard: `/etc/umap/umap.conf`)
- `UMAP_DATABASE_ENV` - Pfad zur `database.env` Datei (Standard: automatisch gesucht)

**Container-Konfiguration:**
- `UMAP_CONTAINER_NAME` - Container-Name (Standard: `umap_app`)

### Sonstiges

- Skripte können auch einzeln ausgeführt werden, müssen dann aber im uMap-Container ausgeführt werden
- Die Scripte nutzen Django's Datenbankverbindung

