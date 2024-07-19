# Nützliche Kommandos

## Logging

### Logrotate

Plugin: /roles/common/action_plugins/common_action_plugin_logrotate.py

Beispiel:

```
- name: Set up log rotation for updatedb.service file /var/log/osm2pgsql-updates.log
  common_action_plugin_logrotate:
    name: osm2pgsql-updates-log
    content:
      - dest: "/var/log/osm2pgsql-updates.log"
        settings:
          - daily
          - rotate 7
          - compress
          - delaycompress
          - missingok
          - notifempty
          - create 0640 root root
```

PR: https://gitlab.fossgis.de/osm-server/ansible_openstreetmap.de/-/merge_requests/68

### Systemd

Beispiel:

```...
ExecStart=/bin/sh -c 'osm2pgsql-replication update -d {{ dbname }} --max-diff-size 10 \
  --diff-file {{ difffile }} --post-processing {{ expiretiles }} -- \
  -G --slim -C 0 -O flex \
  --number-processes {{ ansible_facts['processor_cores'] }} -S {{ lua }} \
  2>&1 | logger -t osm2pgsql-replication'
...
```

Der `ExecStart`-Befehl ist nun in einem `/bin/sh -c`-Konstrukt eingewickelt, damit die Ausgabe umgeleitet werden kann. `2>&1` leitet sowohl die Standardausgabe (stdout) als auch die Standardfehlerausgabe (stderr) an `logger` weiter. `logger -t osm2pgsql-replication` stellt sicher, dass die Ausgabe mit dem Tag `osm2pgsql-replication` versehen wird, was das Filtern im Journal erleichtert.

#### Logs anzeigen

Um die Logs von `osm2pgsql-replication` anzusehen, verwendet man den folgenden Befehl:

```sh
journalctl -t osm2pgsql-replication
```

Dies zeigt alle Logs an, die mit dem Tag `osm2pgsql-replication` versehen sind.

#### Optionen für `journalctl`

**Nur aktuelle Logs anzeigen**: Um nur die neuesten Logs anzuzeigen und die Ausgabe kontinuierlich zu aktualisieren (ähnlich wie `tail -f`):

```sh
journalctl -t osm2pgsql-replication -f
```

**Logs innerhalb eines bestimmten Zeitraums anzeigen**: Um Logs innerhalb eines bestimmten Zeitraums anzuzeigen, kann man die `--since` und `--until` Optionen verwenden. Zum Beispiel, um die Logs der letzten Stunde anzuzeigen:

```sh
journalctl -t osm2pgsql-replication --since "1 hour ago"
```

**Logs mit bestimmten Schweregraden anzeigen**: Um nur Logs mit einem bestimmten Schweregrad oder höher anzuzeigen, verwendet man die `-p` Option. Zum Beispiel, um nur Fehler (`err`) und schwerwiegendere Logs anzuzeigen:

```sh
journalctl -t osm2pgsql-replication -p err
```

Die möglichen Optionen für den Parameter `-p`:

1. `emerg` (oder `0`): Notfall - System ist unbenutzbar
2. `alert` (oder `1`): Sofortige Maßnahmen erforderlich
3. `crit` (oder `2`): Kritischer Zustand
4. `err` (oder `3`): Fehler
5. `warning` (oder `4`): Warnung
6. `notice` (oder `5`): Normal, aber signifikant
7. `info` (oder `6`): Informationsmeldung
8. `debug` (oder `7`): Debugging-Meldung

