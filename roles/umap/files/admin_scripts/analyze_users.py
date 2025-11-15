#!/usr/bin/env python3
"""
User-Auswertung für uMap: Analysiert User nach Karten, Layern, Teams und Datenvolumen.

Verwendung:
    python3 analyze_users.py [--top N] [--sort SORT]
    
Beispiele:
    python3 analyze_users.py                              # Top 20 nach Karten-Anzahl
    python3 analyze_users.py --top 50                     # Top 50
    python3 analyze_users.py --sort size                  # Sortiert nach Gesamtgröße
    python3 analyze_users.py --sort layers --top 30       # Top 30 nach Layer-Anzahl
    
Setup:
Im Docker-Container (umap_app):
    docker exec umap_app /venv/bin/python3 /srv/umap/scripts/admin/analyze_users.py [OPTIONS]
    
    Das Script:
    - Nutzt Django's Database-Connection (gleiche wie uMap)
    - Liest Konfiguration aus /etc/umap/umap.conf
    - Verwendet Umgebungsvariablen aus database.env
"""

import os
import sys
import argparse

# Import gemeinsames Utility-Modul
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from umap_utils import setup_django, format_size, format_date, get_layer_file_size

# Django Setup via Utility-Modul
connection = setup_django()

# Django-Imports nach setup_django()
from django.conf import settings
from django.urls import reverse
from django.core.signing import Signer
from umap.models import Map


def get_anonymous_edit_url(map_id):
    """Generiert den anonymen Bearbeitungslink für eine Karte"""
    try:
        map_obj = Map.objects.get(pk=map_id)
        # Nur wenn die Karte keinen Owner hat (anonym)
        if not map_obj.owner:
            signer = Signer()
            signature = signer.sign(str(map_id))
            path = reverse("map_anonymous_edit_url", kwargs={"signature": signature})
            return settings.SITE_URL + path
    except Map.DoesNotExist:
        pass
    except Exception:
        pass
    return None


def analyze_users(cursor, sort_by='maps', limit=20, show_edit_links=False):
    """Analysiert alle User mit ihren Statistiken"""
    
    # Hole alle User mit ihren Statistiken
    cursor.execute("""
        SELECT 
            u.id,
            u.username,
            u.date_joined,
            u.last_login,
            COUNT(DISTINCT m.id) as owned_maps_count,
            COUNT(DISTINCT me.map_id) as editor_maps_count,
            COUNT(DISTINCT t.id) as teams_count,
            COUNT(DISTINCT d.uuid) as total_layers_count
        FROM auth_user u
        LEFT JOIN umap_map m ON m.owner_id = u.id AND m.share_status != 99
        LEFT JOIN umap_map_editors me ON me.user_id = u.id
        LEFT JOIN umap_team_users tu ON tu.user_id = u.id
        LEFT JOIN umap_team t ON t.id = tu.team_id
        LEFT JOIN umap_datalayer d ON d.map_id = m.id AND d.share_status = 0
        GROUP BY u.id, u.username, u.date_joined, u.last_login
        ORDER BY u.id
    """)
    
    users = []
    for row in cursor.fetchall():
        user_id, username, date_joined, last_login, owned_maps_count, editor_maps_count, teams_count, total_layers_count = row
        
        # Berechne Gesamtgröße aller GeoJSON-Dateien
        # Hole alle Maps des Users (als Owner)
        cursor.execute("""
            SELECT m.id
            FROM umap_map m
            WHERE m.owner_id = %s AND m.share_status != 99
        """, [user_id])
        
        total_size = 0
        edit_links = []
        owned_map_ids = []
        for (map_id,) in cursor.fetchall():
            owned_map_ids.append(map_id)
            # Hole alle Layer dieser Karte
            cursor.execute("""
                SELECT d.geojson
                FROM umap_datalayer d
                WHERE d.map_id = %s AND d.share_status = 0
            """, [map_id])
            
            for (geojson_path,) in cursor.fetchall():
                total_size += get_layer_file_size(geojson_path, map_id=map_id)
        
        # Sammle anonyme Bearbeitungslinks wenn gewünscht
        # Prüfe alle anonymen Karten (ohne Owner), die der User bearbeiten kann
        if show_edit_links:
            # Hole anonyme Karten, bei denen der User als Editor eingetragen ist
            cursor.execute("""
                SELECT DISTINCT m.id
                FROM umap_map m
                JOIN umap_map_editors me ON me.map_id = m.id
                WHERE m.owner_id IS NULL 
                  AND me.user_id = %s 
                  AND m.share_status != 99
            """, [user_id])
            
            for (map_id,) in cursor.fetchall():
                edit_url = get_anonymous_edit_url(map_id)
                if edit_url:
                    edit_links.append((map_id, edit_url))
        
        users.append({
            'id': user_id,
            'username': username or '(kein Name)',
            'date_joined': date_joined,
            'last_login': last_login,
            'owned_maps_count': owned_maps_count or 0,
            'editor_maps_count': editor_maps_count or 0,
            'teams_count': teams_count or 0,
            'total_layers_count': total_layers_count or 0,
            'total_size': total_size,
            'edit_links': edit_links if show_edit_links else None,
        })
    
    # Sortiere nach gewählter Metrik
    if sort_by == 'maps':
        users.sort(key=lambda x: x['owned_maps_count'], reverse=True)
    elif sort_by == 'layers':
        users.sort(key=lambda x: x['total_layers_count'], reverse=True)
    elif sort_by == 'size':
        users.sort(key=lambda x: x['total_size'], reverse=True)
    elif sort_by == 'teams':
        users.sort(key=lambda x: x['teams_count'], reverse=True)
    elif sort_by == 'username':
        users.sort(key=lambda x: x['username'].lower())
    else:
        # Default: nach maps
        users.sort(key=lambda x: x['owned_maps_count'], reverse=True)
    
    return users[:limit]


def print_users_table(users, title, sort_by='maps', show_edit_links=False):
    """Gibt eine kompakte Tabelle aus"""
    print(f"\n{title}")
    print("=" * 130)
    
    header = f"{'ID':<6} {'Username':<25} {'Karten':<7} {'Layer':<7} {'Teams':<7} {'Gesamtgröße':>12} {'Zuletzt eingeloggt':<20}"
    print(header)
    print("-" * 130)
    
    for u in users:
        username = (u['username'][:24] if u['username'] else '(kein Name)') if len(u['username']) <= 24 else u['username'][:21] + '...'
        last_login = format_date(u['last_login']) if u['last_login'] else 'N/A'
        
        print(f"{u['id']:<6} {username:<25} {u['owned_maps_count']:<7} {u['total_layers_count']:<7} {u['teams_count']:<7} {format_size(u['total_size']):>12} {last_login:<20}")
        
        # Zeige anonyme Bearbeitungslinks wenn gewünscht
        if show_edit_links and u.get('edit_links'):
            for map_id, edit_url in u['edit_links']:
                print(f"      → Map {map_id}: {edit_url}")
    
    print("=" * 130)


def main():
    parser = argparse.ArgumentParser(
        description='Analysiert uMap-User nach Karten, Layern, Teams und Datenvolumen',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python3 analyze_users.py                              # Top 20 nach Karten-Anzahl (Standard)
  python3 analyze_users.py --sort maps --top 50         # Top 50 nach Karten-Anzahl
  python3 analyze_users.py --sort size                  # Sortiert nach Gesamtgröße
  python3 analyze_users.py --sort layers --top 30       # Top 30 nach Layer-Anzahl
  python3 analyze_users.py --sort teams                  # Sortiert nach Team-Anzahl
  python3 analyze_users.py --sort username               # Alphabetisch nach Username
        """
    )
    
    parser.add_argument(
        '--top',
        type=int,
        default=20,
        help='Anzahl der Top-Einträge (Standard: 20)'
    )
    
    parser.add_argument(
        '--sort',
        choices=['maps', 'layers', 'size', 'teams', 'username'],
        default='maps',
        help='Sortierung (Standard: maps)'
    )
    
    parser.add_argument(
        '--show-edit-links',
        action='store_true',
        help='Zeigt anonyme Bearbeitungslinks für anonyme Karten an'
    )
    
    args = parser.parse_args()
    
    # Bestimme Titel basierend auf Sortierung
    sort_names = {
        'maps': 'Karten-Anzahl',
        'layers': 'Layer-Anzahl',
        'size': 'Gesamtgröße',
        'teams': 'Team-Anzahl',
        'username': 'Username (alphabetisch)'
    }
    sort_name = sort_names.get(args.sort, 'Karten-Anzahl')
    
    try:
        with connection.cursor() as cursor:
            users = analyze_users(cursor, args.sort, args.top, args.show_edit_links)
            print_users_table(users, f"Top {len(users)} User nach {sort_name}", args.sort, args.show_edit_links)
    
    except Exception as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

