Open Source Routing Machine
===========================

Das ansible script für OSRM erwartet etwas konfiguration, um richtig zu funktionieren:

- `osrm__fronthost`
- `osrm__buildhost`

Die Werte müssen dem ansible `inventory_hostname` entsprechen (dem Namen in hosts.ini). Auch richtig gesetzt werden muss der host im profilearea array:

 - `osrm__profilearea: careu: host:`

Aktuell läuft beides auf demselben server, aber das war halt nicht immer so.

## Vagrant

Braucht konfiguration in `host_vars/vagrant.yml`

```
osrm__fronthost: 'vagrant'
osrm__buildhost: 'vagrant'
osrm__small: True
osrm__profilearea:
    careuasi:
      host: "vagrant"
      poly: "{{ osrm_polyeuasi }}"
      area: europe asia
      port: 3330
      profile: "car"
    carafoce:
      host: "vagrant"
      poly: "{{ osrm_polyafoce }}"
      area: africa oceania
      port: 3338
      profile: "car"
    caram:
      host: "vagrant"
      poly: "{{ osrm_polyam }}"
      area: americas
      port: 3331
      profile: "car"
    bikeeuasi:
      host: "vagrant"
      poly: "{{ osrm_polyeuasi }}"
      area: europe asia
      port: 3332
      profile: "bike"
    bikeafoce:
      host: "vagrant"
      poly: "{{ osrm_polyafoce }}"
      area: africa oceania
      port: 3333
      profile: "bike"
    bikeam:
      host: "vagrant"
      poly: "{{ osrm_polyam }}"
      area: americas
      port: 3334
      profile: "bike"
    footeuasi:
      host: "vagrant"
      poly: "{{ osrm_polyeuasi }}"
      area: europe asia
      port: 3335
      profile: "foot"
    footafoce:
      host: "vagrant"
      poly: "{{ osrm_polyafoce }}"
      area: africa oceania
      port: 3336
      profile: "foot"
    footam:
      host: "vagrant"
      poly: "{{ osrm_polyam }}"
      area: americas
      port: 3337
      profile: "foot"
```

