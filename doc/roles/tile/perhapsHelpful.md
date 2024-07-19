# Setup

Setup von tile.openstreetmap.de

## Erstinstallation

Nachdem das Playbook durchgelaufen ist, muss `sudo /usr/local/sbin/import-osm2pgsql` aufgerufen werden, um die Installation zu beenden.

## Verwaltung

### Tirex

Der **tirex-backend-manager** startet und überwacht die Rendering-Prozesse, die tatsächlich die Kartenkachelnoder meta-Daten erzeugen.

Der **tirex-master** ist der Hauptdienst von Tirex, der die Verteilung der Rendering-Aufträge an die verschiedenen Backends übernimmt. Er kümmert sich um die Zuweisung von Jobs, Warteschlangenverwaltung und Priorisierung der Aufträge.

#### Konfiguration

Die Konfigurationsdateien für Tirex befinden sich unter `/etc/tirex`:

- **Backend:** `/etc/tirex/renderer/mapnik.conf`
- **Master:** `/etc/tirex/master.conf`

#### Service

Die Servicedateien für Tirex befinden sich unter `/lib/systemd/system`.

- **Backend:** `/lib/systemd/system/tirex-backend-manager.service`
- **Master:** `/lib/systemd/system/tirex-master.service`

1. **Status überprüfen**
   ```sh
   sudo systemctl status tirex-master
   sudo systemctl status tirex-backend-manager
   ```
   Diese Befehle zeigen den aktuellen Status der Tirex-Dienste an.

2. **Dienste starten**
   ```sh
   sudo systemctl start tirex-master
   sudo systemctl start tirex-backend-manager
   ```
   Diese Befehle starten die Tirex-Dienste.

3. **Dienste stoppen**
   ```sh
   sudo systemctl stop tirex-master
   sudo systemctl stop tirex-backend-manager
   ```
   Diese Befehle stoppen die Tirex-Dienste.

4. **Dienste neu starten**
   ```sh
   sudo systemctl restart tirex-master
   sudo systemctl restart tirex-backend-manager
   ```
   Diese Befehle starten die Tirex-Dienste neu, was nützlich ist, wenn Konfigurationsänderungen vorgenommen wurden.

5. **Konfiguration neu laden**
   ```sh
   sudo systemctl reload tirex-master
   sudo systemctl reload tirex-backend-manager
   ```
   Diese Befehle laden die Konfigurationsdateien neu, ohne die Dienste vollständig neu zu starten.

#### Logging

   ```sh
   sudo journalctl -u tirex-master
   sudo journalctl -u tirex-backend-manager
   ```

   /var/logs/tirex/jobs.log

#### Backend - Verwaltung von Tiles 

(https://wiki.openstreetmap.org/wiki/Tirex/Commands)

1. **Kacheln rendern**

   Um bestimmte Kacheln zu rendern, kann man den Befehl `tirex-batch` verwenden:

   ```sh
   tirex-batch --prio=1 map=osmde z=13 x=6985 y=3172
   ```

2. **Alle Kacheln eines Bereichs rendern**

   Um alle Kacheln in einem bestimmten Bereich zu rendern, kann man den Befehl `tirex-batch` verwenden. Dies ist besonders nützlich, wenn man Kacheln für größere Bereiche generieren möchte:

   ```sh
   tirex-batch --prio=99 map=osmde z=1-3 lon=-180,180 lat=-90,90 --expire +1
   ```
Alle Kacheln mit Zoom 1 bis 3 würden dann ab der nächsten Sekunde veraltet sein. (https://wiki.openstreetmap.org/wiki/Tirex/Commands/tirex-batch)

3. **Status überprüfen**

`tirex-status` oder `tirex-status -o` (o = once).


