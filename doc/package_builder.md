# Debian Pakete erstellen

## VM anlegen

VM via `bash get_debian_vm.sh`erstellen. Für *Mapnik 4.3.2* braucht man mehr Arbeitsspeicher. Ich habe mit 8192 MB getestet.


## Pakete erstellen

Als Beispiel verwende ich *Mapnik 4.3.2*.

Damit das *package_builder-Playbook* ausgeführt wird, muss die `ansible-vm.ini` angepasst werden.

Meine `ansible-vm.ini`

```
[servers]
trixie ansible_host=192.168.137.13
bookworm ansible_host=192.168.137.12

[acme]
dummy

[package_builder]
trixie
```

Danach kann das Playbook gestartet werden. Welches Programm kompiliert wird, legt man via *tags* fest (Momentan: branch packageBuilder)!

`ansible-playbook --private-key vm/id_ed25519 -l trixie -i ansible-vm.ini package_builder.yml --tags "mapnik,always"` 

Wenn alles passt befinden sich am Ende im Verzeichnis `/vm/packages/trixie` des Playbooks die kompilierten Dateien. Im Falle von *Mapnik 4.3.2* sind das

```
ansible_openstreetmap.de/vm/packages/trixie$ ls
libmapnik-dev_4.3.2-1+osmde_amd64.deb  mapnik_4.3.2-1+osmde_amd64.deb  tirex_0.8.0-1_amd64.deb  tirex-munin-plugin_0.8.0-1_amd64.deb  tirex-nagios-plugin_0.8.0-1_amd64.deb
```

## Pakete testen

Das Tag "test" sorgt dafür, dass nur der Task zum *Testen der Installation* aufgerufen wird.

### Tile-Rolle testen

*Mapnik 4.3.2* ist für die Tileserver. Deshalb teste ich mit der Tile-Rolle

(Branch master und OSM_SOURCE in `roles/tile/templates/import-osm2pgsql.j2` sinnvoll setzten. Für Mapnik 4.3.2 Test https://download.geofabrik.de/asia/sri-lanka-latest.osm.pbf eintragen)

#### VM anlegen

VM via `bash get_debian_vm.sh`erstellen. Für die Tile-Rolle braucht man mehr Arbeitsspeicher. Ich habe mit 8192 MB getestet.

#### ansible-vm.ini

Die `ansible-vm.ini` so ändern, dass sie die Tile Rolle ausführt.

```
[servers]
trixie ansible_host=192.168.137.13
bookworm ansible_host=192.168.137.12

[acme]
dummy

[package_builder]
dummy

[tile]
trixie
```

#### Playbook aufrufen

Dann das Playbook aufrufen via

`ansible-playbook --private-key vm/id_ed25519 -l trixie -i ansible-vm.ini site.yml`

#### Datenbank erstellen

Danach via `ssh -i vm/id_ed25519 root@192.168.137.13` in die VM wechseln und `sudo /usr/local/sbin/import-osm2pgsql` aufrufen, damit die Datenbank erstellt wird.

Ergebnis: https://192.168.137.13/ zeigt im Browser die Website an und der Name Sri Lanka wird im deutschen Stil als Tofu falsch dargestellt.

#### Selbstkompilierte Pakete installieren

(nun zurück zum packageBuilder branch `git checkout packageBuilder`) 

Die `ansible-vm.ini` so ändern, dass sie die `package_builder` Rolle ausführt.

```
[servers]
trixie ansible_host=192.168.137.13
bookworm ansible_host=192.168.137.12

[acme]
dummy

[package_builder]
trixie

[tile]
dummy

```

`ansible-playbook --private-key vm/id_ed25519 -l trixie -i ansible-vm.ini package_builder.yml --tags "test"`
installiert alle Pakete aus dem Ansible-Playbook-Verzeichnis `/vm/packages/trixie` und prüft Abhängigkeiten.

Ergebnis: https://192.168.137.13/ zeigt im Browser die Website an und der Sri Lanka wird nun auch im deutschen Stil korrekt dargestellt. Falls es nicht direkt funktioniert. Das Löschen des Browser Cache reicht oft nicht. Man muss auch in der VM das Verzeichnis `/var/cache/tirex/tiles/osmde/` aufräumen.
