#!/usr/bin/env python3
"""
Setzt oder entfernt API-Keys in Tile-URLs der uMap-Datenbank.

Provider werden in TILELAYER_APIKEYS (umap.conf) oder UMAP_TILELAYER_APIKEYS
konfiguriert.

Aktualisiert:
- umap_tilelayer.url_template (Auswahl im Karteneditor)
- umap_map.settings properties.tilelayer / properties.overlay (bestehende Karten)

Verwendung:
    python3 update_tilelayer_apikeys.py [--dry-run]
    python3 update_tilelayer_apikeys.py --remove KEY [--provider NAME] [--dry-run]

Setup:
Im Docker-Container (umap_app):
    docker exec umap_app /venv/bin/python3 /srv/umap/scripts/admin/update_tilelayer_apikeys.py [--dry-run]

    Das Script:
    - Nutzt Django's Database-Connection (gleiche wie uMap)
    - Liest Provider aus /etc/umap/umap.conf (TILELAYER_APIKEYS)
    - Verwendet Umgebungsvariablen aus database.env

Ausgabe:
    - stderr: Detail-Logs und lesbare Zusammenfassung
    - stdout: eine JSON-Zeile mit Ergebnis (fuer Ansible: changed, tilelayers, maps)
"""

import argparse
import ast
import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from umap_utils import get_umap_basedir, get_umap_settings_path, setup_django

MAP_FIELDS = ("tilelayer", "overlay")


def _normalize_providers(raw):
    if isinstance(raw, str):
        raw = json.loads(raw)
    providers = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        match = item.get("match") or []
        if isinstance(match, str):
            match = [match]
        param = str(item.get("param", "")).strip()
        value = str(item.get("value", "")).strip()
        placeholder = item.get("placeholder")
        if placeholder is not None:
            placeholder = str(placeholder)
        if not name or not match or not param:
            continue
        providers.append(
            {
                "name": name,
                "match": [m.lower() for m in match if m],
                "param": param,
                "value": value,
                "placeholder": placeholder,
            }
        )
    return providers


def _load_tilelayer_apikeys_from_conf_regex(text):
    legacy = re.search(
        r"TILELAYER_APIKEYS\s*=\s*json\.loads\(\s*'''(.+?)'''\s*\)",
        text,
        re.DOTALL,
    )
    if legacy:
        return json.loads(legacy.group(1))
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("TILELAYER_APIKEYS"):
            continue
        _, _, value = stripped.partition("=")
        value = value.strip()
        if value.startswith("["):
            return ast.literal_eval(value)
    return None


def _conf_paths():
    paths = []
    for path in (
        os.getenv("UMAP_SETTINGS"),
        "/etc/umap/umap.conf",
        str(Path(get_umap_basedir()) / "umap.conf"),
    ):
        if path and path not in paths and os.path.isfile(path):
            paths.append(path)
    return paths


def _load_tilelayer_apikeys_from_file(path):
    text = Path(path).read_text(encoding="utf-8")
    parsed = _load_tilelayer_apikeys_from_conf_regex(text)
    if parsed is not None:
        return parsed, None
    namespace = {}
    try:
        exec(compile(text, path, "exec"), namespace)
    except Exception as exc:
        return None, f"TILELAYER_APIKEYS aus {path} nicht lesbar: {exc}"
    if "TILELAYER_APIKEYS" not in namespace:
        return None, f"TILELAYER_APIKEYS fehlt in {path}"
    return namespace["TILELAYER_APIKEYS"], None


def _load_tilelayer_apikeys_from_conf_exec():
    errors = []
    for path in _conf_paths():
        raw, error = _load_tilelayer_apikeys_from_file(path)
        if error:
            errors.append(error)
        if raw is not None:
            return raw, None
    if errors:
        return None, "; ".join(errors)
    return None, "Keine umap.conf gefunden"


def load_providers():
    attempts = []
    if os.getenv("UMAP_TILELAYER_APIKEYS"):
        attempts.append(("UMAP_TILELAYER_APIKEYS", os.environ["UMAP_TILELAYER_APIKEYS"]))

    conf_raw, conf_error = _load_tilelayer_apikeys_from_conf_exec()
    if conf_error:
        print(conf_error, file=sys.stderr)
    if conf_raw is not None:
        attempts.append((get_umap_settings_path(), conf_raw))

    try:
        import umap.settings as umap_settings

        if hasattr(umap_settings, "TILELAYER_APIKEYS"):
            attempts.append(("umap.settings", umap_settings.TILELAYER_APIKEYS))
    except Exception as exc:
        print(f"TILELAYER_APIKEYS aus umap.settings nicht lesbar: {exc}", file=sys.stderr)

    for _label, raw in attempts:
        providers = _normalize_providers(raw)
        if providers:
            return providers
    return []


@lru_cache(maxsize=None)
def param_pattern(param):
    return re.compile(rf"([?&]){re.escape(param)}=([^&]*)", re.IGNORECASE)


def find_provider(url, providers):
    if not url or not isinstance(url, str):
        return None
    lower = url.lower()
    for provider in providers:
        if any(marker in lower for marker in provider["match"]):
            return provider
    return None


def get_param_value(url, param):
    match = param_pattern(param).search(url)
    if not match:
        return None
    return unquote(match.group(2))


def cleanup_query(url):
    url = re.sub(r"\?&", "?", url)
    url = re.sub(r"\?$", "", url)
    url = re.sub(r"&$", "", url)
    return url


def apply_key_to_url(url, provider, key):
    param = provider["param"]
    placeholder = provider.get("placeholder")
    encoded_key = quote(key, safe="")

    if placeholder and placeholder in url:
        return url.replace(placeholder, encoded_key, 1)

    existing = get_param_value(url, param)
    if existing is not None:
        if unquote(existing) == key:
            return url
        return param_pattern(param).sub(rf"\1{param}={encoded_key}", url, count=1)

    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{param}={encoded_key}"


def remove_key_from_url(url, provider, key_to_remove):
    param = provider["param"]
    placeholder = provider.get("placeholder")
    encoded_remove = quote(key_to_remove, safe="")

    existing = get_param_value(url, param)
    if existing is not None and unquote(existing) == key_to_remove:
        new_url = param_pattern(param).sub("", url, count=1)
        return cleanup_query(new_url)

    if placeholder:
        if encoded_remove in url:
            return url.replace(encoded_remove, placeholder, 1)
        if key_to_remove in url:
            return url.replace(key_to_remove, placeholder, 1)

    return url


def transform_url(url, provider, remove_key=None):
    if remove_key is not None:
        return remove_key_from_url(url, provider, remove_key)
    return apply_key_to_url(url, provider, provider["value"])


def filter_providers(providers, provider_name=None, require_value=False):
    result = []
    for provider in providers:
        if provider_name and provider["name"] != provider_name:
            continue
        if require_value and not provider["value"]:
            continue
        result.append(provider)
    return result


def emit_result(tilelayers, maps, dry_run):
    """Schreibt Zusammenfassung nach stderr und maschinenlesbares Ergebnis nach stdout."""
    changed = tilelayers > 0 or maps > 0
    prefix = "Dry-run: " if dry_run else ""
    print(
        f"{prefix}Updated {tilelayers} tilelayers, {maps} maps",
        file=sys.stderr,
    )
    print(
        json.dumps(
            {
                "changed": changed,
                "tilelayers": tilelayers,
                "maps": maps,
                "dry_run": dry_run,
            }
        ),
        flush=True,
    )


def fail(message, exit_code=1):
    print(message, file=sys.stderr)
    print(
        json.dumps({"changed": False, "error": message}),
        flush=True,
    )
    sys.exit(exit_code)


def update_tilelayers(providers, dry_run, remove_key=None):
    from umap.models import TileLayer

    updated = 0
    for layer in TileLayer.objects.all():
        provider = find_provider(layer.url_template, providers)
        if provider is None:
            continue
        new_url = transform_url(layer.url_template, provider, remove_key)
        if new_url == layer.url_template:
            continue
        print(
            f"tilelayer {layer.pk} '{layer.name}' [{provider['name']}]: "
            f"{layer.url_template} -> {new_url}",
            file=sys.stderr,
        )
        if not dry_run:
            layer.url_template = new_url
            layer.save(update_fields=["url_template"])
        updated += 1
    return updated


def update_maps(providers, dry_run, remove_key=None):
    from django.db import connection

    updated = 0
    with connection.cursor() as cursor:
        for field in MAP_FIELDS:
            cursor.execute(
                "SELECT DISTINCT settings->'properties'->%s->>'url_template' "
                "FROM umap_map "
                "WHERE settings->'properties'->%s->>'url_template' IS NOT NULL",
                [field, field],
            )
            urls = [row[0] for row in cursor.fetchall()]
            for old_url in urls:
                provider = find_provider(old_url, providers)
                if provider is None:
                    continue
                new_url = transform_url(old_url, provider, remove_key)
                if new_url == old_url:
                    continue
                if dry_run:
                    cursor.execute(
                        "SELECT COUNT(*) FROM umap_map "
                        "WHERE settings->'properties'->%s->>'url_template' = %s",
                        [field, old_url],
                    )
                    count = cursor.fetchone()[0]
                    print(
                        f"maps {field} [{provider['name']}]: {count}x "
                        f"{old_url} -> {new_url}",
                        file=sys.stderr,
                    )
                    updated += count
                    continue
                cursor.execute(
                    "UPDATE umap_map "
                    f"SET settings['properties']['{field}']['url_template'] "
                    "= to_jsonb(%s::text) "
                    "WHERE settings->'properties'->%s->>'url_template' = %s",
                    [new_url, field, old_url],
                )
                print(
                    f"maps {field} [{provider['name']}]: {cursor.rowcount}x "
                    f"{old_url} -> {new_url}",
                    file=sys.stderr,
                )
                updated += cursor.rowcount
    return updated


def main():
    parser = argparse.ArgumentParser(
        description="API-Keys an Tile-URLs in der uMap-Datenbank setzen oder entfernen."
    )
    parser.add_argument(
        "--remove",
        metavar="KEY",
        help="Nur diesen exakten Key-Wert entfernen (param=KEY)",
    )
    parser.add_argument(
        "--provider",
        metavar="NAME",
        help="Nur diesen Provider (name aus TILELAYER_APIKEYS)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur anzeigen, nicht speichern",
    )
    args = parser.parse_args()

    setup_django()
    all_providers = load_providers()
    if not all_providers:
        fail(
            "Keine Provider in TILELAYER_APIKEYS konfiguriert. "
            f"Config: {get_umap_settings_path()}"
        )

    if args.provider and not any(p["name"] == args.provider for p in all_providers):
        fail(f"FEHLER: Unbekannter Provider '{args.provider}'.")

    if args.remove is not None:
        remove_key = os.getenv("UMAP_REMOVE_KEY") or args.remove
        providers = filter_providers(all_providers, args.provider, require_value=False)
        if not remove_key:
            fail("FEHLER: --remove erfordert einen KEY.")
        tilelayers = update_tilelayers(providers, args.dry_run, remove_key=remove_key)
        maps = update_maps(providers, args.dry_run, remove_key=remove_key)
    else:
        providers = filter_providers(all_providers, args.provider, require_value=True)
        if not providers:
            print(
                "Keine Provider mit gesetztem value. Nichts zu tun.",
                file=sys.stderr,
            )
            emit_result(0, 0, args.dry_run)
            sys.exit(0)
        tilelayers = update_tilelayers(providers, args.dry_run)
        maps = update_maps(providers, args.dry_run)

    emit_result(tilelayers, maps, args.dry_run)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        fail(f"FEHLER: {exc}")
