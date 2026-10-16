# Aptly

## Testen in VM

VM via `bash get_debian_vm.sh`neu erstellen. (Achtung: Wegen `nginx` kann nicht auf einer "gebrauchten" VM aufgebaut werden, die Apache nutzt)

## Playbook aufrufen

Als Beispiel verwende ich *Mapnik 4.3.2*. Die Deb-Dateien müssen im Playbook erstellt worden sein und sich im Verzeichnis `vm/packages/` in einem Verzeichnis mit dem Namen der Distribution befinden:

```
<vm/packages/
└── trixie/
    ├── libmapnik-dev_4.3.2-1+osmde_amd64.deb
    ├── mapnik_4.3.2-1+osmde_amd64.deb
    ├── tirex_0.8.0-1_amd64.deb
    ├── tirex-munin-plugin_0.8.0-1_amd64.deb
    └── tirex-nagios-plugin_0.8.0-1_amd64.deb
```

Damit das *aptly-Playbook* ausgeführt wird, muss die `ansible-vm.ini` angepasst werden.

Meine `ansible-vm.ini`

```
[servers]
trixie ansible_host=192.168.137.13
bookworm ansible_host=192.168.137.12

[acme]
dummy

[aptly]
trixie
```

Dann sind zwei Aufrufe notwendig.
1. `ansible-playbook --private-key vm/id_ed25519 -l trixie -i ansible-vm.ini site.yml` um alle Tasks außer denen mit dem Tag `aptly_upload` auszuführen. Dies passiert dann auch bei jedem Lauf auf Robinson.
2. `ansible-playbook --private-key vm/id_ed25519 -l trixie -i ansible-vm.ini site.yml --tags "aptly_upload"` um Deb-Dateien im Verzeichnis `/vm/packages` zu veröffentlichen.

## Test 

### Via Browser

https://192.168.137.13/ zeigt im Browser die Pakete analog zu https://apt.openstreetmap.org/dists/trixie/ an

### Bash

```
root@OSM-server-debian-trixie:~# aptly repo list  
List of local repos:
 * [osm-tileserver-de-trixie] (packages: 5)

To get more information about local repository, run `aptly repo show <name>`.
root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# aptly repo show osm-tileserver-de-trixie
Name: osm-tileserver-de-trixie
Comment: 
Default Distribution: trixie
Default Component: main
Number of packages: 5
root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# aptly repo show -with-packages osm-tileserver-de-trixie 
Name: osm-tileserver-de-trixie
Comment: 
Default Distribution: trixie
Default Component: main
Number of packages: 5
Packages:
  libmapnik-dev_4.3.2-1+osmde_amd64
  mapnik_4.3.2-1+osmde_amd64
  tirex_0.8.0-1_amd64
  tirex-munin-plugin_0.8.0-1_amd64
  tirex-nagios-plugin_0.8.0-1_amd64
root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# aptly repo search osm-tileserver-de-trixie mapnik
mapnik_4.3.2-1+osmde_amd64
root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# aptly package show mapnik_4.3.2-1+osmde_amd64
Package: mapnik
Priority: optional
Section: libs
Installed-Size: 31892
Maintainer: example.org <info@example.org>
Architecture: amd64
Version: 4.3.2-1+osmde
Depends: libboost-context1.83.0 (>= 1.83.0), libboost-program-options1.83.0 (>= 1.83.0), libboost-url1.83.0 (>= 1.83.0), libc6 (>= 2.38), libfreetype6 (>= 2.2.1), libgcc-s1 (>= 3.0), libharfbuzz0b (>= 1.6.0), libicu76 (>= 76.1-1~), libjpeg62-turbo (>= 1.3.1), libpng16-16t64 (>= 1.6.46), libpq5, libproj25 (>= 8.0.0), libsqlite3-0 (>= 3.5.9), libstdc++6 (>= 14), libtiff6 (>= 4.0.3), libwebp7 (>= 1.5.0), zlib1g (>= 1:1.1.4)
Filename: mapnik_4.3.2-1+osmde_amd64.deb
Size: 6378604
MD5sum: 25e3c76da175d5f7ad2b7050cfa089a9
SHA1: a0190d7fddcaf7d301245d1145872b07d71d147c
SHA256: 7100bf14f1a713d8eeb6eb32cf05e5d62dc760c8f602c770844330c42275caaa
SHA512: 36d65b83cd361c977c0fb49f5a1d6d782204d9af1b7590b79c15083cf60396e6681f4e9e171137d1c2766bf4e667a10fcc9cc59c1d09193b291fa5f341b31344
Description: Mapnik mapping toolkit
 C++ library for rendering maps and geospatial data.

root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# aptly publish list  
Published repositories:
  * ./trixie [amd64] publishes {main: [osm-tileserver-de-trixie]}
root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# 
root@OSM-server-debian-trixie:~# aptly publish show trixie
Prefix: .
Distribution: trixie
Architectures: amd64
Sources:
  main: osm-tileserver-de-trixie [local]

```

## Optional

Falls auf dem Server `robinson` getestet wird, ist es angeraten via `host_vars/trixie.yml` die Variable `acme__debug_mode: true` zu setzten.
