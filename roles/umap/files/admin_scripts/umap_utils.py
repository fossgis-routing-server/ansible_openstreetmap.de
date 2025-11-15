#!/usr/bin/env python3
"""
Gemeinsames Utility-Modul für uMap Admin-Skripte.

Dieses Modul enthält gemeinsame Funktionen für alle uMap Admin-Skripte:
- Django-Setup und Datenbankverbindung
- Dateigrößen-Formatierung
- Datumsformatierung
- Container-Erkennung
- MEDIA_ROOT-Konfiguration
"""

import os
import sys
from pathlib import Path
from django.utils import timezone


def get_script_dir():
    """Ermittelt das Verzeichnis, in dem dieses Script liegt"""
    return Path(__file__).parent.absolute()


def _is_in_container_simple():
    """Einfache Container-Erkennung ohne Abhängigkeiten"""
    # Standard Docker-Erkennung
    if os.path.exists("/.dockerenv"):
        return True
    
    # Zusätzliche Prüfung: uMap-spezifischer entrypoint
    if os.path.exists("/srv/umap/docker/entrypoint.sh"):
        return True
    
    return False


def get_umap_basedir():
    """Ermittelt das uMap Base-Verzeichnis mit Fallback-Mechanismus"""
    # 1. Umgebungsvariable (höchste Priorität)
    if os.getenv("UMAP_BASEDIR"):
        return os.getenv("UMAP_BASEDIR")
    
    # 2. Container-Erkennung (einfache Prüfung ohne Rekursion)
    if _is_in_container_simple():
        return "/srv/umap"
    
    # 3. Relativ zum Script-Verzeichnis (für lokale Entwicklung)
    script_dir = get_script_dir()
    # Versuche typische Verzeichnisstrukturen zu erkennen
    possible_basedirs = [
        script_dir.parent.parent,  # Script in admin_scripts/, basedir 2 Ebenen höher
        script_dir.parent,         # Script direkt im basedir
        Path("/srv/umap"),         # Standard-Host-Pfad
    ]
    
    for basedir in possible_basedirs:
        # Prüfe ob es ein uMap-Verzeichnis ist (hat typischerweise umapdata/ oder docker/)
        if (basedir / "umapdata").exists() or (basedir / "docker").exists():
            return str(basedir)
    
    # 4. Fallback auf Standard
    return "/srv/umap"


def is_in_container():
    """Prüft ob das Script im Docker-Container läuft"""
    # Standard Docker-Erkennung
    if _is_in_container_simple():
        return True
    
    # Zusätzliche Prüfung: uMap-spezifische Pfade basierend auf basedir
    basedir = get_umap_basedir()
    entrypoint_path = Path(basedir) / "docker" / "entrypoint.sh"
    return entrypoint_path.exists()


def get_media_root():
    """Ermittelt den MEDIA_ROOT-Pfad basierend auf Umgebung"""
    # 1. Umgebungsvariable (höchste Priorität)
    if os.getenv("UMAP_MEDIA_ROOT"):
        return os.getenv("UMAP_MEDIA_ROOT")
    
    # 2. Basierend auf Umgebung und basedir
    basedir = get_umap_basedir()
    if is_in_container():
        return str(Path(basedir) / "media_root")
    else:
        return str(Path(basedir) / "umapdata" / "media_root")


def get_umap_settings_path():
    """Ermittelt den Pfad zur uMap-Konfigurationsdatei"""
    # 1. Umgebungsvariable (höchste Priorität)
    if os.getenv("UMAP_SETTINGS"):
        return os.getenv("UMAP_SETTINGS")
    
    # 2. Standard-Pfade
    standard_paths = [
        "/etc/umap/umap.conf",
        str(Path(get_umap_basedir()) / "umap.conf"),
    ]
    
    for path in standard_paths:
        if os.path.exists(path):
            return path
    
    # 3. Fallback
    return "/etc/umap/umap.conf"


def load_database_env():
    """Lädt Umgebungsvariablen aus database.env (falls vorhanden)"""
    # Ermittle basedir für relative Pfade
    basedir = get_umap_basedir()
    
    # Priorisierte Liste von Suchpfaden
    # Ansible erstellt die Datei immer unter /srv/umap/database.env,
    # aber wir suchen auch an anderen Orten für Flexibilität
    database_env_paths = [
        # 1. Umgebungsvariable (höchste Priorität - für Tests/Überschreibung)
        os.getenv("UMAP_DATABASE_ENV"),
        # 2. Im basedir (Standard-Ansible-Pfad, funktioniert im Container und auf Host)
        str(Path(basedir) / "database.env"),
        # 3. Relativ zum aktuellen Arbeitsverzeichnis (für docker-compose, das ./database.env verwendet)
        "./database.env",
    ]
    
    # Entferne None-Werte (falls UMAP_DATABASE_ENV nicht gesetzt)
    database_env_paths = [p for p in database_env_paths if p]
    
    for env_path in database_env_paths:
        try:
            env_path = os.path.normpath(env_path)
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            # Setze nur wenn noch nicht gesetzt
                            if key not in os.environ:
                                os.environ[key] = value
                return True
        except (OSError, IOError):
            continue
    
    return False


def setup_django():
    """Initialisiert Django und stellt die Datenbankverbindung her"""
    # Lade database.env falls vorhanden
    load_database_env()
    
    # Django Setup für Datenbank-Zugriff
    basedir = get_umap_basedir()
    sys.path.insert(0, basedir)
    
    # Verwende 'umap.settings' statt 'umap.settings.base', damit __init__.py
    # ausgeführt wird und die lokalen Einstellungen aus umap.conf geladen werden
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umap.settings')
    
    # Setze UMAP_SETTINGS mit robuster Pfad-Ermittlung
    if 'UMAP_SETTINGS' not in os.environ:
        os.environ['UMAP_SETTINGS'] = get_umap_settings_path()
    
    try:
        import django
        from django.conf import settings
        
        # Stelle sicher, dass POSTGRES_HOST gesetzt ist, bevor Django lädt
        if not os.getenv('POSTGRES_HOST'):
            # Fallback: Im Container sollte es "db" sein
            if os.path.exists("/.dockerenv"):
                os.environ['POSTGRES_HOST'] = "db"
        
        django.setup()
        
        # Überschreibe Datenbank-Einstellungen falls Umgebungsvariablen gesetzt sind
        from django.conf import settings
        if 'POSTGRES_HOST' in os.environ:
            settings.DATABASES['default']['HOST'] = os.getenv('POSTGRES_HOST')
        if 'POSTGRES_DB' in os.environ:
            settings.DATABASES['default']['NAME'] = os.getenv('POSTGRES_DB')
        if 'POSTGRES_USER' in os.environ:
            settings.DATABASES['default']['USER'] = os.getenv('POSTGRES_USER')
        if 'POSTGRES_PASSWORD' in os.environ:
            settings.DATABASES['default']['PASSWORD'] = os.getenv('POSTGRES_PASSWORD')
        if 'POSTGRES_PORT' in os.environ:
            settings.DATABASES['default']['PORT'] = os.getenv('POSTGRES_PORT')
        
        # Schließe bestehende Verbindungen, damit neue Einstellungen genutzt werden
        from django.db import connections
        connections.close_all()
        
        from django.db import connection
        return connection
        
    except ImportError:
        print("FEHLER: Django ist nicht verfügbar. Script muss im uMap-Container ausgeführt werden.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"FEHLER: Django konnte nicht initialisiert werden: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def format_size(size_bytes):
    """Formatiert Bytes in lesbare Größe"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def format_date(dt, include_time=False):
    """Formatiert Datum kompakt
    
    Args:
        dt: datetime-Objekt oder None
        include_time: Wenn True, füge Zeit hinzu (Standard: False)
    
    Returns:
        Formatierter Datums-String oder "N/A"
    """
    if not dt:
        return "N/A"
    if include_time:
        return dt.strftime("%Y-%m-%d %H:%M")
    else:
        return dt.strftime("%Y-%m-%d")


def format_days_ago(dt):
    """Berechnet Tage seit Datum
    
    Args:
        dt: datetime-Objekt oder None (muss timezone-aware sein)
    
    Returns:
        String wie "5d" oder "N/A"
    """
    if not dt:
        return "N/A"
    try:
        delta = timezone.now() - dt
        return f"{delta.days}d"
    except Exception:
        # Fallback für timezone-naive datetime
        from datetime import datetime
        if dt.tzinfo is None:
            # Versuche mit timezone.now() zu vergleichen, falls möglich
            try:
                delta = timezone.now().replace(tzinfo=None) - dt
                return f"{delta.days}d"
            except:
                return "N/A"
        return "N/A"


def get_layer_file_size(geojson_path, map_id=None):
    """Ermittelt die Dateigröße eines Layers
    
    Args:
        geojson_path: Relativer oder absoluter Pfad zur GeoJSON-Datei
        map_id: Optional, wird für Fallback-Suche verwendet
    
    Returns:
        Dateigröße in Bytes (0 wenn Datei nicht gefunden)
    """
    if not geojson_path:
        return 0
    
    MEDIA_ROOT = get_media_root()
    
    # Wenn bereits absolut, direkt prüfen
    if os.path.isabs(geojson_path):
        file_path = Path(geojson_path)
        if file_path.exists():
            return file_path.stat().st_size
        return 0
    
    # Relativer Pfad: Kombiniere mit MEDIA_ROOT
    file_path = Path(MEDIA_ROOT) / geojson_path
    if file_path.exists():
        return file_path.stat().st_size
    
    # Fallback: Suche im Standard-Verzeichnis basierend auf map_id (wenn vorhanden)
    if map_id:
        map_str = str(map_id)
        path_parts = ["datalayer", map_str[-1]]
        if len(map_str) > 1:
            path_parts.append(map_str[-2])
        path_parts.append(map_str)
        
        # Wenn der geojson_path ein Dateiname ist, suche im Verzeichnis
        filename = Path(geojson_path).name
        if filename and filename.endswith('.geojson'):
            fallback_path = Path(MEDIA_ROOT) / Path(*path_parts) / filename
            if fallback_path.exists():
                return fallback_path.stat().st_size
    
    return 0


def format_share_status(share_status):
    """Formatiert share_status als o (öffentlich) oder p (privat)
    
    Args:
        share_status: Integer-Wert des Share-Status
    
    Returns:
        "ö" für öffentlich (PUBLIC=1, OPEN=2), "p" für privat
    """
    # PUBLIC = 1, DRAFT = 0, PRIVATE = 3, OPEN = 2, BLOCKED = 9, DELETED = 99
    if share_status == 1:  # PUBLIC
        return "ö"
    elif share_status == 2:  # OPEN (Anyone with link)
        return "ö"
    else:  # DRAFT (0), PRIVATE (3), etc.
        return "p"


# MEDIA_ROOT als Modul-Variable für Rückwärtskompatibilität
MEDIA_ROOT = get_media_root()

