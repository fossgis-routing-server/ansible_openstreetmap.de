#!/usr/bin/env python3
"""
Kartenauswertung für uMap: Analysiert Karten nach Größe und Aktivität.

Verwendung:
    python3 analyze_maps.py [--top N] [--metric METRIC] [--days DAYS]
    
Beispiele:
    python3 analyze_maps.py                              # Top 20 nach Größe
    python3 analyze_maps.py --top 50                      # Top 50
    python3 analyze_maps.py --metric activity             # Top 20 aktivste Karten
    python3 analyze_maps.py --metric layers --top 30      # Top 30 nach Layer-Anzahl
    python3 analyze_maps.py --metric inactive --days 90  # Inaktive Karten (>90 Tage)
    
Setup:
Im Docker-Container (umap_app):
    docker exec umap_app /venv/bin/python3 /srv/umap/scripts/admin/analyze_maps.py [OPTIONS]
    
    Das Script:
    - Nutzt Django's Database-Connection (gleiche wie uMap)
    - Liest Konfiguration aus /etc/umap/umap.conf
    - Verwendet Umgebungsvariablen aus database.env
"""

import os
import sys
import argparse
from datetime import timedelta
from collections import defaultdict
from django.utils import timezone

# Import gemeinsames Utility-Modul
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from umap_utils import setup_django, format_size, format_date, format_days_ago, get_layer_file_size

# Django Setup via Utility-Modul
connection = setup_django()


def analyze_maps_by_size(cursor, limit=20):
    """Analysiert Karten nach Gesamtgröße aller GeoJSON-Dateien"""
    cursor.execute("""
        SELECT 
            m.id,
            m.name,
            m.slug,
            m.created_at,
            m.modified_at,
            m.share_status,
            u.username as owner_username,
            COUNT(d.uuid) as layer_count,
            SUM(CASE 
                WHEN d.geojson IS NOT NULL THEN 1 ELSE 0 
            END) as layers_with_files
        FROM umap_map m
        LEFT JOIN auth_user u ON m.owner_id = u.id
        LEFT JOIN umap_datalayer d ON d.map_id = m.id AND d.share_status = 0
        WHERE m.share_status != 99
        GROUP BY m.id, m.name, m.slug, m.created_at, m.modified_at, m.share_status, u.username
        HAVING COUNT(d.uuid) > 0
        ORDER BY m.id
    """)
    
    maps = []
    for row in cursor.fetchall():
        map_id, name, slug, created_at, modified_at, share_status, owner_username, layer_count, layers_with_files = row
        
        # Berechne Gesamtgröße aller Layer
        cursor.execute("""
            SELECT d.geojson
            FROM umap_datalayer d
            WHERE d.map_id = %s AND d.share_status = 0
        """, [map_id])
        
        total_size = 0
        max_layer_size = 0
        for (geojson_path,) in cursor.fetchall():
            size = get_layer_file_size(geojson_path, map_id=map_id)
            total_size += size
            max_layer_size = max(max_layer_size, size)
        
        maps.append({
            'id': map_id,
            'name': name or '(kein Name)',
            'slug': slug,
            'owner_username': owner_username,
            'created_at': created_at,
            'modified_at': modified_at,
            'share_status': share_status,
            'layer_count': layer_count,
            'total_size': total_size,
            'max_layer_size': max_layer_size,
        })
    
    # Sortiere nach Gesamtgröße (absteigend)
    maps.sort(key=lambda x: x['total_size'], reverse=True)
    return maps[:limit]


def analyze_maps_by_layers(cursor, limit=20):
    """Analysiert Karten nach Anzahl der Layer"""
    cursor.execute("""
        SELECT 
            m.id,
            m.name,
            m.slug,
            m.created_at,
            m.modified_at,
            m.share_status,
            u.username as owner_username,
            COUNT(d.uuid) as layer_count
        FROM umap_map m
        LEFT JOIN auth_user u ON m.owner_id = u.id
        LEFT JOIN umap_datalayer d ON d.map_id = m.id AND d.share_status = 0
        WHERE m.share_status != 99
        GROUP BY m.id, m.name, m.slug, m.created_at, m.modified_at, m.share_status, u.username
        HAVING COUNT(d.uuid) > 0
        ORDER BY COUNT(d.uuid) DESC, m.id
        LIMIT %s
    """, [limit])
    
    maps = []
    for row in cursor.fetchall():
        map_id, name, slug, created_at, modified_at, share_status, owner_username, layer_count = row
        
        # Berechne Größen
        cursor.execute("""
            SELECT d.geojson
            FROM umap_datalayer d
            WHERE d.map_id = %s AND d.share_status = 0
        """, [map_id])
        
        total_size = 0
        max_layer_size = 0
        for (geojson_path,) in cursor.fetchall():
            size = get_layer_file_size(geojson_path, map_id=map_id)
            total_size += size
            max_layer_size = max(max_layer_size, size)
        
        maps.append({
            'id': map_id,
            'name': name or '(kein Name)',
            'slug': slug,
            'owner_username': owner_username,
            'created_at': created_at,
            'modified_at': modified_at,
            'share_status': share_status,
            'layer_count': layer_count,
            'total_size': total_size,
            'max_layer_size': max_layer_size,
        })
    
    return maps


def analyze_maps_by_activity(cursor, limit=20):
    """Analysiert Karten nach Aktivität (modified_at)"""
    cursor.execute("""
        SELECT 
            m.id,
            m.name,
            m.slug,
            m.created_at,
            m.modified_at,
            m.share_status,
            u.username as owner_username,
            COUNT(d.uuid) as layer_count,
            MAX(d.modified_at) as last_layer_modified
        FROM umap_map m
        LEFT JOIN auth_user u ON m.owner_id = u.id
        LEFT JOIN umap_datalayer d ON d.map_id = m.id AND d.share_status = 0
        WHERE m.share_status != 99
        GROUP BY m.id, m.name, m.slug, m.created_at, m.modified_at, m.share_status, u.username
        HAVING COUNT(d.uuid) > 0
        ORDER BY GREATEST(m.modified_at, COALESCE(MAX(d.modified_at), m.modified_at)) DESC
        LIMIT %s
    """, [limit])
    
    maps = []
    for row in cursor.fetchall():
        map_id, name, slug, created_at, modified_at, share_status, owner_username, layer_count, last_layer_modified = row
        
        # Berechne Größen
        cursor.execute("""
            SELECT d.geojson
            FROM umap_datalayer d
            WHERE d.map_id = %s AND d.share_status = 0
        """, [map_id])
        
        total_size = 0
        for (geojson_path,) in cursor.fetchall():
            total_size += get_layer_file_size(geojson_path, map_id)
        
        maps.append({
            'id': map_id,
            'name': name or '(kein Name)',
            'slug': slug,
            'owner_username': owner_username,
            'created_at': created_at,
            'modified_at': modified_at,
            'last_layer_modified': last_layer_modified,
            'share_status': share_status,
            'layer_count': layer_count,
            'total_size': total_size,
        })
    
    return maps


def analyze_inactive_maps(cursor, limit=20):
    """Analysiert die ältesten inaktiven Karten (sortiert nach letzter Aktivität)"""
    cursor.execute("""
        SELECT 
            m.id,
            m.name,
            m.slug,
            m.created_at,
            m.modified_at,
            m.share_status,
            u.username as owner_username,
            COUNT(d.uuid) as layer_count,
            MAX(d.modified_at) as last_layer_modified,
            GREATEST(m.modified_at, COALESCE(MAX(d.modified_at), m.modified_at)) as last_activity
        FROM umap_map m
        LEFT JOIN auth_user u ON m.owner_id = u.id
        LEFT JOIN umap_datalayer d ON d.map_id = m.id AND d.share_status = 0
        WHERE m.share_status != 99
        GROUP BY m.id, m.name, m.slug, m.created_at, m.modified_at, m.share_status, u.username
        HAVING COUNT(d.uuid) > 0
        ORDER BY GREATEST(m.modified_at, COALESCE(MAX(d.modified_at), m.modified_at)) ASC
        LIMIT %s
    """, [limit])
    
    maps = []
    for row in cursor.fetchall():
        map_id, name, slug, created_at, modified_at, share_status, owner_username, layer_count, last_layer_modified, last_activity_db = row
        
        # Berechne Größen
        cursor.execute("""
            SELECT d.geojson
            FROM umap_datalayer d
            WHERE d.map_id = %s AND d.share_status = 0
        """, [map_id])
        
        total_size = 0
        for (geojson_path,) in cursor.fetchall():
            total_size += get_layer_file_size(geojson_path, map_id)
        
        # Verwende last_activity_db direkt aus der Query (bereits berechnet)
        last_activity = last_activity_db if last_activity_db else modified_at
        days_inactive = (timezone.now() - last_activity).days
        
        maps.append({
            'id': map_id,
            'name': name or '(kein Name)',
            'slug': slug,
            'owner_username': owner_username,
            'created_at': created_at,
            'modified_at': modified_at,
            'last_layer_modified': last_layer_modified,
            'days_inactive': days_inactive,
            'share_status': share_status,
            'layer_count': layer_count,
            'total_size': total_size,
        })
    
    return maps


def analyze_largest_layers(cursor, limit=20):
    """Analysiert die größten einzelnen Layer"""
    cursor.execute("""
        SELECT 
            d.uuid::text as layer_uuid,
            d.name,
            d.geojson,
            d.map_id,
            m.name as map_name,
            m.slug,
            u.username as owner_username,
            d.modified_at
        FROM umap_datalayer d
        JOIN umap_map m ON d.map_id = m.id
        LEFT JOIN auth_user u ON m.owner_id = u.id
        WHERE d.share_status = 0 AND m.share_status != 99
    """)
    
    layers = []
    for row in cursor.fetchall():
        layer_uuid, name, geojson_path, map_id, map_name, slug, owner_username, modified_at = row
        
        size = get_layer_file_size(geojson_path, map_id)
        if size > 0:
            layers.append({
                'layer_uuid': layer_uuid,
                'name': name or '(kein Name)',
                'map_id': map_id,
                'map_name': map_name or '(kein Name)',
                'slug': slug,
                'owner_username': owner_username,
                'modified_at': modified_at,
                'size': size,
            })
    
    # Sortiere nach Größe
    layers.sort(key=lambda x: x['size'], reverse=True)
    return layers[:limit]


def print_maps_table(maps, title, show_activity=False, show_inactive=False):
    """Gibt eine kompakte Tabelle aus"""
    print(f"\n{title}")
    print("=" * 160)
    
    if show_inactive:
        header = f"{'ID':<8} {'Layer':<6} {'Größe':>10} {'Inaktiv':<8} {'Name':<25} {'Slug':<25} {'User':<18} {'Zuletzt geändert':<20}"
    elif show_activity:
        header = f"{'ID':<8} {'Layer':<6} {'Größe':>10} {'Name':<25} {'Slug':<25} {'User':<18} {'Aktivität':<20}"
    else:
        header = f"{'ID':<8} {'Layer':<6} {'Größe':>10} {'Größter Layer':>12} {'Name':<25} {'Slug':<25} {'User':<18} {'Geändert':<20}"
    
    print(header)
    print("-" * 160)
    
    for m in maps:
        name = (m['name'][:24] if m['name'] else '(kein Name)') if len(m.get('name', '')) <= 24 else m['name'][:21] + '...'
        slug = (m['slug'][:24] if m['slug'] else 'N/A') if len(m.get('slug', '')) <= 24 else m['slug'][:21] + '...'
        user = m['owner_username'][:17] if m['owner_username'] else 'anonym'
        
        if show_inactive:
            days = str(m['days_inactive']) + 'd'
            modified = format_date(m['last_layer_modified'] or m['modified_at'], include_time=True)
            print(f"{m['id']:<8} {m['layer_count']:<6} {format_size(m['total_size']):>10} {days:<8} {name:<25} {slug:<25} {user:<18} {modified:<20}")
        elif show_activity:
            last_activity = m['last_layer_modified'] if m['last_layer_modified'] and m['last_layer_modified'] > m['modified_at'] else m['modified_at']
            activity = format_days_ago(last_activity)
            print(f"{m['id']:<8} {m['layer_count']:<6} {format_size(m['total_size']):>10} {name:<25} {slug:<25} {user:<18} {activity:<20}")
        else:
            max_layer = format_size(m.get('max_layer_size', 0))
            modified = format_days_ago(m['modified_at'])
            print(f"{m['id']:<8} {m['layer_count']:<6} {format_size(m['total_size']):>10} {max_layer:>12} {name:<25} {slug:<25} {user:<18} {modified:<20}")
    
    print("=" * 160)


def print_layers_table(layers, title):
    """Gibt eine Tabelle der größten Layer aus"""
    print(f"\n{title}")
    print("=" * 140)
    header = f"{'Layer-UUID':<38} {'Größe':>10} {'Layer-Name':<30} {'Map-ID':<8} {'Map-Name':<30} {'User':<20} {'Geändert':<20}"
    print(header)
    print("-" * 140)
    
    for l in layers:
        layer_name = (l['name'][:29] if l['name'] else '(kein Name)') if len(l['name']) <= 29 else l['name'][:26] + '...'
        map_name = (l['map_name'][:29] if l['map_name'] else '(kein Name)') if len(l['map_name']) <= 29 else l['map_name'][:26] + '...'
        user = l['owner_username'][:19] if l['owner_username'] else 'anonym'
        modified = format_days_ago(l['modified_at'])
        uuid_short = l['layer_uuid'][:8] + '...' if len(l['layer_uuid']) > 8 else l['layer_uuid']
        
        print(f"{uuid_short:<38} {format_size(l['size']):>10} {layer_name:<30} {l['map_id']:<8} {map_name:<30} {user:<20} {modified:<20}")
    
    print("=" * 140)


def main():
    parser = argparse.ArgumentParser(
        description='Analysiert uMap-Karten nach Größe und Aktivität',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python3 analyze_maps.py                              # Top 20 nach Gesamtgröße
  python3 analyze_maps.py --top 50                      # Top 50 nach Größe
  python3 analyze_maps.py --metric layers               # Top 20 nach Layer-Anzahl
  python3 analyze_maps.py --metric activity             # Top 20 aktivste Karten
  python3 analyze_maps.py --metric inactive             # Inaktive Karten (sortiert nach Alter)
  python3 analyze_maps.py --metric largest-layers        # Größte einzelne Layer
        """
    )
    
    parser.add_argument(
        '--top',
        type=int,
        default=20,
        help='Anzahl der Top-Einträge (Standard: 20)'
    )
    
    parser.add_argument(
        '--metric',
        choices=['size', 'layers', 'activity', 'inactive', 'largest-layers'],
        default='size',
        help='Metrik für die Auswertung (Standard: size)'
    )
    
    
    args = parser.parse_args()
    
    try:
        with connection.cursor() as cursor:
            if args.metric == 'size':
                maps = analyze_maps_by_size(cursor, args.top)
                print_maps_table(maps, f"Top {len(maps)} Karten nach Gesamtgröße")
            
            elif args.metric == 'layers':
                maps = analyze_maps_by_layers(cursor, args.top)
                print_maps_table(maps, f"Top {len(maps)} Karten nach Layer-Anzahl")
            
            elif args.metric == 'activity':
                maps = analyze_maps_by_activity(cursor, args.top)
                print_maps_table(maps, f"Top {len(maps)} aktivste Karten", show_activity=True)
            
            elif args.metric == 'inactive':
                maps = analyze_inactive_maps(cursor, limit=args.top)
                print_maps_table(maps, f"Top {len(maps)} älteste inaktive Karten", show_inactive=True)
            
            elif args.metric == 'largest-layers':
                layers = analyze_largest_layers(cursor, args.top)
                print_layers_table(layers, f"Top {len(layers)} größte einzelne Layer")
    
    except Exception as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

