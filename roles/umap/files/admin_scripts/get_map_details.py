#!/usr/bin/env python3
# Im Container: Nutzt /venv/bin/python3 falls vorhanden, sonst System-Python
"""
Gibt alle Layer einer uMap-Karte mit ihren GeoJSON-Dateipfaden aus.

Verwendung:
    python3 get_map_details.py <map_id>
    python3 get_map_details.py <url>
    
Beispiele:
    python3 get_map_details.py <MAP_ID>
    python3 get_map_details.py https://umap.example.com/de/map/karte_<MAP_ID>/
    python3 get_map_details.py /de/map/karte_<MAP_ID>/
    
Setup:

Im Docker-Container (umap_app):
    # Nutzt Django's Datenbankverbindung - keine zusätzlichen Dependencies nötig!
    docker exec umap_app /venv/bin/python3 /srv/umap/scripts/admin/get_map_details.py <map_id>
    
    Das Script:
    - Nutzt Django's Database-Connection (gleiche wie uMap)
    - Liest Konfiguration aus /etc/umap/umap.conf
    - Verwendet Umgebungsvariablen aus database.env (via env_file)
"""

import os
import sys
import re
import argparse
from pathlib import Path

# Import gemeinsames Utility-Modul
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from umap_utils import setup_django, format_size, get_media_root

# Django Setup via Utility-Modul
connection = setup_django()

# Django-Imports nach setup_django()
from umap.models import Map

# MEDIA_ROOT aus Utility-Modul
MEDIA_ROOT = get_media_root()


def get_anonymous_edit_url(map_id):
    """Generiert den anonymen Bearbeitungslink für eine anonyme Karte"""
    try:
        map_obj = Map.objects.get(pk=map_id)
        # Nur wenn die Karte keinen Owner hat (anonym)
        if not map_obj.owner:
            # Nutze die vorhandene Methode aus dem Map-Model
            return map_obj.get_anonymous_edit_url()
    except Map.DoesNotExist:
        pass
    except Exception as e:
        # Fehlerbehandlung für Debugging
        print(f"WARNUNG: Konnte anonymen Bearbeitungslink nicht generieren: {e}", file=sys.stderr)
    return None


def extract_map_id(input_value):
    """Extrahiert die Map-ID aus einer URL oder gibt die ID direkt zurück"""
    # Wenn es eine Zahl ist, direkt zurückgeben
    try:
        map_id = int(input_value)
        return map_id
    except ValueError:
        pass
    
    # Versuche Map-ID aus URL zu extrahieren
    # URL-Formate:
    # - /map/slug_mapid/
    # - /map/mapid/
    # - https://domain/de/map/slug_mapid/
    # - https://domain/de/map/mapid/
    patterns = [
        r'/map/(?:[\w-]+_)?(\d+)',  # /map/slug_<MAP_ID> oder /map/<MAP_ID>
        r'map_id=(\d+)',              # ?map_id=<MAP_ID>
        r'id=(\d+)',                  # ?id=<MAP_ID>
    ]
    
    for pattern in patterns:
        match = re.search(pattern, input_value)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    return None


def get_layer_path(geojson_path, map_id):
    """Ermittelt den vollständigen Pfad zur GeoJSON-Datei"""
    if not geojson_path:
        return None
    
    # Wenn bereits absolut, direkt zurückgeben
    if os.path.isabs(geojson_path):
        file_path = Path(geojson_path)
        if file_path.exists():
            return file_path
        return None
    
    # Relativer Pfad: Kombiniere mit MEDIA_ROOT
    file_path = Path(MEDIA_ROOT) / geojson_path
    if file_path.exists():
        return file_path
    
    # Fallback: Suche im Standard-Verzeichnis basierend auf map_id
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
            return fallback_path
    
    # Wenn Datei nicht gefunden, gib den erwarteten Pfad zurück
    return Path(MEDIA_ROOT) / geojson_path


def get_map_layers(map_id, show_edit_link=False):
    """Holt alle Layer einer Karte aus der Datenbank via Django"""
    try:
        with connection.cursor() as cursor:
            # Hole Map-Informationen inklusive Timestamps
            # Prüfe welche Spalten verfügbar sind
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'umap_map' 
                  AND table_schema = 'public'
                ORDER BY ordinal_position
            """)
            map_columns = [row[0] for row in cursor.fetchall()]
            
            # Baue SELECT-Query dynamisch basierend auf verfügbaren Spalten
            select_fields = ['id', 'name', 'slug']
            if 'created_at' in map_columns:
                select_fields.append('created_at')
            else:
                select_fields.append('NULL as created_at')
            if 'modified_at' in map_columns:
                select_fields.append('modified_at')
            else:
                select_fields.append('NULL as modified_at')
            if 'description' in map_columns:
                select_fields.append('description')
            else:
                select_fields.append('NULL as description')
            
            # Hole Owner-Information mit JOIN
            owner_join = ""
            owner_select = ", NULL as owner_username, NULL as owner_id"
            if 'owner_id' in map_columns:
                owner_join = "LEFT JOIN auth_user u ON m.owner_id = u.id"
                owner_select = ", u.username as owner_username, m.owner_id"
            
            # Baue SELECT-Query mit Tabellenpräfix
            select_with_prefix = []
            for field in select_fields:
                if field.startswith('NULL as '):
                    select_with_prefix.append(field)
                else:
                    select_with_prefix.append(f'm.{field}')
            
            cursor.execute(f"""
                SELECT {', '.join(select_with_prefix)}{owner_select}
                FROM umap_map m
                {owner_join}
                WHERE m.id = %s
            """, [map_id])
            
            map_info = cursor.fetchone()
            if not map_info:
                print(f"FEHLER: Karte mit ID {map_id} nicht gefunden.", file=sys.stderr)
                return None
            
            map_id_db = map_info[0]
            map_name = map_info[1]
            map_slug = map_info[2]
            map_created_at = map_info[3] if len(map_info) > 3 else None
            map_modified_at = map_info[4] if len(map_info) > 4 else None
            map_description = map_info[5] if len(map_info) > 5 else None
            owner_username = map_info[6] if len(map_info) > 6 else None
            owner_id = map_info[7] if len(map_info) > 7 else None
            
            # Hole alle weiteren Maps des Users (wenn nicht anonym)
            user_map_ids = []
            if owner_id:
                cursor.execute("""
                    SELECT DISTINCT m.id
                    FROM umap_map m
                    LEFT JOIN umap_map_editors me ON m.id = me.map_id
                    WHERE (m.owner_id = %s OR me.user_id = %s)
                      AND m.id != %s
                      AND m.share_status != 99
                    ORDER BY m.id
                """, [owner_id, owner_id, map_id])
                user_map_ids = [row[0] for row in cursor.fetchall()]
            
            # Hole alle Layer der Karte mit zusätzlichen Informationen
            # description kann NULL sein, settings ist JSON
            cursor.execute("""
                SELECT 
                    d.uuid::text,
                    d.name,
                    d.description,
                    d.geojson,
                    d.rank,
                    d.display_on_load,
                    d.modified_at,
                    d.settings
                FROM umap_datalayer d
                WHERE d.map_id = %s
                  AND d.share_status = 0
                ORDER BY d.rank, d.modified_at DESC
            """, [map_id])
            
            layers = []
            for row in cursor.fetchall():
                uuid, name, description, geojson_path, rank, display_on_load, modified_at, settings_json = row
                
                file_path = get_layer_path(geojson_path, map_id)
                
                # Ermittle Dateigröße
                size_bytes = 0
                if file_path and file_path.exists():
                    size_bytes = file_path.stat().st_size
                
                layers.append({
                    'uuid': uuid,
                    'name': name or '(kein Name)',
                    'description': description,
                    'geojson_path': geojson_path,
                    'file_path': str(file_path) if file_path else geojson_path or '(nicht gefunden)',
                    'exists': file_path.exists() if file_path else False,
                    'size_bytes': size_bytes,
                    'rank': rank,
                    'display_on_load': display_on_load,
                    'modified_at': modified_at,
                    'settings': settings_json,
                })
            
            # Generiere anonymen Bearbeitungslink wenn gewünscht und Karte anonym ist
            anonymous_edit_url = None
            if show_edit_link:
                if not owner_id:
                    anonymous_edit_url = get_anonymous_edit_url(map_id_db)
                # Wenn owner_id vorhanden ist, bleibt anonymous_edit_url None
                # (nur anonyme Karten haben anonyme Bearbeitungslinks)
            
            return {
                'map_id': map_id_db,
                'map_name': map_name,
                'map_slug': map_slug,
                'map_description': map_description,
                'map_created_at': map_created_at,
                'map_modified_at': map_modified_at,
                'owner_username': owner_username,
                'owner_id': owner_id,
                'user_map_ids': user_map_ids,
                'layers': layers,
                'anonymous_edit_url': anonymous_edit_url
            }
        
    except Exception as e:
        print(f"FEHLER: Datenbankverbindung fehlgeschlagen: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Zeigt Details einer uMap-Karte inklusive aller Layer und GeoJSON-Dateipfade',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'map_identifier',
        help='Map-ID oder URL'
    )
    
    parser.add_argument(
        '--show-edit-link',
        action='store_true',
        help='Zeigt den anonymen Bearbeitungslink an (nur für anonyme Karten)'
    )
    
    args = parser.parse_args()
    
    map_id = extract_map_id(args.map_identifier)
    
    if map_id is None:
        print(f"FEHLER: Konnte keine Map-ID aus '{args.map_identifier}' extrahieren.", file=sys.stderr)
        sys.exit(1)
    
    result = get_map_layers(map_id, args.show_edit_link)
    
    if result is None:
        sys.exit(1)
    
    # Map-Informationen (platzsparend)
    info_parts = [f"Karte: {result['map_name']} (ID: {result['map_id']})"]
    if result['owner_username']:
        info_parts.append(f"User: {result['owner_username']}")
    elif not result['owner_id']:
        info_parts.append("Anonym")
    if result['map_slug']:
        info_parts.append(f"Slug: {result['map_slug']}")
    print(" | ".join(info_parts))
    
    if result['map_description']:
        print(f"Beschreibung: {result['map_description']}")
    
    # Anonymer Bearbeitungslink
    if result.get('anonymous_edit_url'):
        print(f"Anonymer Bearbeitungslink: {result['anonymous_edit_url']}")
    
    date_info = []
    if result['map_created_at']:
        date_info.append(f"Erstellt: {result['map_created_at']}")
    if result['map_modified_at']:
        date_info.append(f"Bearbeitet: {result['map_modified_at']}")
    if date_info:
        print(" | ".join(date_info))
    
    # Weitere Maps des Users (platzsparend)
    if result['user_map_ids']:
        map_ids_str = ", ".join(str(mid) for mid in result['user_map_ids'])
        print(f"Weitere Maps ({len(result['user_map_ids'])}): {map_ids_str}")
    
    print("=" * 120)
    
    if not result['layers']:
        print(f"Keine Layer für Karte {map_id} gefunden.")
        return
    
    # Layer-Übersichtstabelle mit vollständigem Pfad
    print(f"\n{'Rank':<5} {'Größe':>10} {'Name':<40} {'Zuletzt bearbeitet':<20}")
    print("-" * 120)
    
    total_size = 0
    for layer in result['layers']:
        status = "[OK]" if layer['exists'] else "[FEHLT]"
        size_str = format_size(layer['size_bytes']) if layer['exists'] else "N/A"
        total_size += layer['size_bytes']
        name = layer['name'][:39] if layer['name'] else '(kein Name)'
        modified_str = str(layer['modified_at'])[:19] if layer['modified_at'] else 'N/A'
        
        print(f"{layer['rank']:>5} {status} {size_str:>9} {name:<40} {modified_str:<20}")
        print(f"     GeoJSON: {layer['file_path']}")
    
    print("-" * 120)
    print(f"{'GESAMT':<5} {format_size(total_size):>10} {len(result['layers'])} Layer")
    
    # Konvertiere Container-Pfade zu Host-Pfaden
    def container_to_host_path(container_path):
        """Konvertiert Container-Pfad zu Host-Pfad"""
        if not container_path:
            return container_path
        # Container-Pfad: /srv/umap/media_root/...
        # Host-Pfad: /srv/umap/umapdata/media_root/...
        if container_path.startswith('/srv/umap/media_root/'):
            return container_path.replace('/srv/umap/media_root/', '/srv/umap/umapdata/media_root/', 1)
        return container_path
    
    # Ausgabe im einfachen Format für Skripte (Host-Pfade)
    print("\n" + "=" * 120)
    print("Pfade zu den GeoJSON-Dateien (auf dem Host):")
    print("=" * 120)
    for layer in result['layers']:
        host_path = container_to_host_path(layer['file_path'])
        if layer['exists']:
            print(host_path)
        else:
            print(f"# {host_path} (Datei nicht gefunden)")


if __name__ == "__main__":
    main()

