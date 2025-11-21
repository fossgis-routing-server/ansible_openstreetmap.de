#!/usr/bin/env python3
"""
User-Detail-Auswertung für uMap: Zeigt detaillierte Informationen zu einem User.

Verwendung:
    python3 get_user_details.py <user_id> | <username>
    
Beispiele:
    python3 get_user_details.py <USER_ID>
    python3 get_user_details.py <username>
    
Setup:
Im Docker-Container (umap_app):
    docker exec umap_app /venv/bin/python3 /srv/umap/scripts/admin/get_user_details.py <user_id>
    
    Das Script:
    - Nutzt Django's Database-Connection (gleiche wie uMap)
    - Liest Konfiguration aus /etc/umap/umap.conf
    - Verwendet Umgebungsvariablen aus database.env
"""

import os
import sys
from django.utils import timezone

# Import gemeinsames Utility-Modul
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from umap_utils import (
    setup_django, format_size, format_date, format_days_ago,
    format_share_status, get_layer_file_size
)

# Django Setup via Utility-Modul
connection = setup_django()


def get_user_by_id_or_username(cursor, identifier):
    """Sucht User nach ID oder Username"""
    try:
        user_id = int(identifier)
        cursor.execute("""
            SELECT id, username, date_joined, last_login
            FROM auth_user
            WHERE id = %s
        """, [user_id])
    except ValueError:
        cursor.execute("""
            SELECT id, username, date_joined, last_login
            FROM auth_user
            WHERE username = %s
        """, [identifier])
    
    row = cursor.fetchone()
    if not row:
        return None
    
    user_id, username, date_joined, last_login = row
    return {
        'id': user_id,
        'username': username,
        'date_joined': date_joined,
        'last_login': last_login,
    }


def get_user_details(cursor, user_id):
    """Holt alle Details zu einem User"""
    # User-Grundinformationen
    cursor.execute("""
        SELECT id, username, date_joined, last_login
        FROM auth_user
        WHERE id = %s
    """, [user_id])
    
    user_row = cursor.fetchone()
    if not user_row:
        return None
    
    user_id_db, username, date_joined, last_login = user_row
    
    # Hole eigene Karten
    cursor.execute("""
        SELECT 
            m.id,
            m.name,
            m.slug,
            m.created_at,
            m.modified_at,
            m.share_status,
            COUNT(d.uuid) as layer_count
        FROM umap_map m
        LEFT JOIN umap_datalayer d ON d.map_id = m.id AND d.share_status = 0
        WHERE m.owner_id = %s AND m.share_status != 99
        GROUP BY m.id, m.name, m.slug, m.created_at, m.modified_at, m.share_status
        ORDER BY m.modified_at DESC
    """, [user_id])
    
    owned_maps = []
    total_layers = 0
    total_size = 0
    max_map_size = 0
    oldest_map = None
    newest_map = None
    
    for row in cursor.fetchall():
        map_id, map_name, map_slug, map_created_at, map_modified_at, share_status, layer_count = row
        
        # Berechne Größe dieser Karte
        cursor.execute("""
            SELECT d.geojson
            FROM umap_datalayer d
            WHERE d.map_id = %s AND d.share_status = 0
        """, [map_id])
        
        map_size = 0
        for (geojson_path,) in cursor.fetchall():
            size = get_layer_file_size(geojson_path, map_id=map_id)
            map_size += size
        
        total_size += map_size
        total_layers += layer_count or 0
        max_map_size = max(max_map_size, map_size)
        
        if not oldest_map or map_created_at < oldest_map['created_at']:
            oldest_map = {'id': map_id, 'name': map_name, 'created_at': map_created_at}
        if not newest_map or map_created_at > newest_map['created_at']:
            newest_map = {'id': map_id, 'name': map_name, 'created_at': map_created_at}
        
        owned_maps.append({
            'id': map_id,
            'name': map_name or '(kein Name)',
            'slug': map_slug,
            'created_at': map_created_at,
            'modified_at': map_modified_at,
            'share_status': share_status,
            'layer_count': layer_count or 0,
            'size': map_size,
        })
    
    # Sortiere Karten nach Größe
    owned_maps_sorted_by_size = sorted(owned_maps, key=lambda x: x['size'], reverse=True)
    
    # Hole Editor-Karten
    cursor.execute("""
        SELECT DISTINCT m.id, m.name, m.slug, m.modified_at, m.share_status
        FROM umap_map m
        JOIN umap_map_editors me ON me.map_id = m.id
        WHERE me.user_id = %s AND m.share_status != 99
        ORDER BY m.modified_at DESC
    """, [user_id])
    
    editor_maps = []
    for row in cursor.fetchall():
        map_id, map_name, map_slug, map_modified_at, share_status = row
        editor_maps.append({
            'id': map_id,
            'name': map_name or '(kein Name)',
            'slug': map_slug,
            'modified_at': map_modified_at,
            'share_status': share_status,
        })
    
    # Hole Teams
    cursor.execute("""
        SELECT 
            t.id,
            t.name,
            COUNT(DISTINCT tu.user_id) as member_count
        FROM umap_team t
        JOIN umap_team_users tu ON tu.team_id = t.id
        WHERE tu.user_id = %s
        GROUP BY t.id, t.name
        ORDER BY t.name
    """, [user_id])
    
    teams = []
    for row in cursor.fetchall():
        team_id, team_name, member_count = row
        teams.append({
            'id': team_id,
            'name': team_name,
            'member_count': member_count or 0,
        })
    
    # Berechne Statistiken
    avg_map_size = total_size / len(owned_maps) if owned_maps else 0
    # PUBLIC = 1, OPEN = 2 (beide gelten als öffentlich)
    public_maps = sum(1 for m in owned_maps if m['share_status'] in [1, 2])
    private_maps = len(owned_maps) - public_maps
    
    return {
        'user': {
            'id': user_id_db,
            'username': username,
            'date_joined': date_joined,
            'last_login': last_login,
        },
        'owned_maps': owned_maps,
        'owned_maps_sorted_by_size': owned_maps_sorted_by_size,
        'editor_maps': editor_maps,
        'teams': teams,
        'stats': {
            'owned_maps_count': len(owned_maps),
            'editor_maps_count': len(editor_maps),
            'teams_count': len(teams),
            'total_layers': total_layers,
            'total_size': total_size,
            'max_map_size': max_map_size,
            'avg_map_size': avg_map_size,
            'public_maps': public_maps,
            'private_maps': private_maps,
            'oldest_map': oldest_map,
            'newest_map': newest_map,
        }
    }


def print_user_details(details):
    """Gibt User-Details übersichtlich aus"""
    user = details['user']
    stats = details['stats']
    
    print("=" * 120)
    print(f"User: {user['username']} (ID: {user['id']})")
    print("=" * 120)
    
    # Grundinformationen
    print(f"Account erstellt: {format_date(user['date_joined'], include_time=True)} ({format_days_ago(user['date_joined'])} alt)")
    print(f"Letzter Login: {format_date(user['last_login'], include_time=True) if user['last_login'] else 'N/A'} ({format_days_ago(user['last_login']) if user['last_login'] else 'N/A'})")
    print()
    
    # Statistiken
    print("Statistiken:")
    print("-" * 120)
    print(f"  Eigene Karten:        {stats['owned_maps_count']}")
    print(f"  Karten als Editor:    {stats['editor_maps_count']}")
    print(f"  Teams:                {stats['teams_count']}")
    print(f"  Layer (gesamt):       {stats['total_layers']}")
    print(f"  Gesamtgröße:          {format_size(stats['total_size'])}")
    print(f"  Größte Karte:         {format_size(stats['max_map_size'])}")
    print(f"  Durchschnitt:         {format_size(stats['avg_map_size'])}")
    print(f"  Öffentliche Karten:   {stats['public_maps']}")
    print(f"  Private Karten:       {stats['private_maps']}")
    if stats['oldest_map']:
        print(f"  Älteste Karte:        ID {stats['oldest_map']['id']} ({format_date(stats['oldest_map']['created_at'])})")
    if stats['newest_map']:
        print(f"  Neueste Karte:        ID {stats['newest_map']['id']} ({format_date(stats['newest_map']['created_at'])})")
    print()
    
    # Eigene Karten
    if details['owned_maps']:
        print(f"Eigene Karten ({len(details['owned_maps'])}):")
        print("-" * 120)
        header = f"{'ID':<8} {'S':<2} {'Layer':<7} {'Größe':>12} {'Name':<30} {'Zuletzt geändert':<20}"
        print(header)
        print("-" * 120)
        
        for m in details['owned_maps']:
            name = (m['name'][:29] if m['name'] else '(kein Name)') if len(m['name']) <= 29 else m['name'][:26] + '...'
            modified = format_date(m['modified_at'], include_time=True) if m['modified_at'] else 'N/A'
            status = format_share_status(m['share_status'])
            
            print(f"{m['id']:<8} {status:<2} {m['layer_count']:<7} {format_size(m['size']):>12} {name:<30} {modified:<20}")
            if m['slug']:
                print(f"     Slug: {m['slug']}")
        
        print()
        
        # Top 5 größte Karten
        if len(details['owned_maps_sorted_by_size']) > 0:
            print("Top 5 größte Karten:")
            print("-" * 120)
            for i, m in enumerate(details['owned_maps_sorted_by_size'][:5], 1):
                name = (m['name'][:29] if m['name'] else '(kein Name)') if len(m['name']) <= 29 else m['name'][:26] + '...'
                print(f"  {i}. ID {m['id']}: {name} - {format_size(m['size'])}")
            print()
    else:
        print("Keine eigenen Karten")
        print()
    
    # Editor-Karten
    if details['editor_maps']:
        print(f"Karten als Editor ({len(details['editor_maps'])}):")
        print("-" * 120)
        header = f"{'ID':<8} {'Name':<30} {'Zuletzt geändert':<20}"
        print(header)
        print("-" * 120)
        
        for m in details['editor_maps']:
            name = (m['name'][:29] if m['name'] else '(kein Name)') if len(m['name']) <= 29 else m['name'][:26] + '...'
            modified = format_date(m['modified_at'], include_time=True) if m['modified_at'] else 'N/A'
            
            print(f"{m['id']:<8} {name:<30} {modified:<20}")
            if m['slug']:
                print(f"     Slug: {m['slug']}")
        print()
    else:
        print("Keine Karten als Editor")
        print()
    
    # Teams
    if details['teams']:
        print(f"Teams ({len(details['teams'])}):")
        print("-" * 120)
        header = f"{'ID':<8} {'Name':<40} {'Mitglieder':<10}"
        print(header)
        print("-" * 120)
        
        for t in details['teams']:
            name = (t['name'][:39] if t['name'] else '(kein Name)') if len(t['name']) <= 39 else t['name'][:36] + '...'
            print(f"{t['id']:<8} {name:<40} {t['member_count']:<10}")
        print()
    else:
        print("Keine Teams")
        print()
    
    print("=" * 120)


def main():
    if len(sys.argv) < 2:
        print("Verwendung: python3 get_user_details.py <user_id> | <username>")
        print("\nBeispiele:")
        print("  python3 get_user_details.py <USER_ID>")
        print("  python3 get_user_details.py <username>")
        sys.exit(1)
    
    identifier = sys.argv[1]
    
    try:
        with connection.cursor() as cursor:
            # Suche User
            user = get_user_by_id_or_username(cursor, identifier)
            if not user:
                print(f"FEHLER: User '{identifier}' nicht gefunden.", file=sys.stderr)
                sys.exit(1)
            
            # Hole Details
            details = get_user_details(cursor, user['id'])
            if not details:
                print(f"FEHLER: Konnte Details für User '{identifier}' nicht laden.", file=sys.stderr)
                sys.exit(1)
            
            # Ausgabe
            print_user_details(details)
    
    except Exception as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

