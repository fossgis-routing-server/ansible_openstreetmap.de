Webserver Konfiguration
=======================

Das Ansible-Repo enthält Rollen, um nginx oder Apache aufzusetzen. Um die Rollen
zu verwenden, fügt man entsprechende Abhängigkeiten in der `meta/main.yml` der
Rolle ein, die den Webserver benötigt.

Site-Konfiguration
------------------

Beide Rollen definieren Aktionen, um Sites zu installieren, `nginx_site` und
`apache_site`. Beide installieren eine Site-Konfiguration im entsprechenden
Verzeichnis `sites-available` und setzen Links in `sites-enabled`. Die Aktionen
nehmen die folgenden Parameter:

= site:  (string) Name der Site und Dateiname unter dem die Site-Konfiguration
         gespeichert wird.
= src:   (file) Template-Datei mit der Site-Konfiguration.
- state: 'present' erstellt/aktualisiert die Site-Konfiguration und
         aktiviert sie. 'absent' entfernt den Link aus `sites-enabled`.
         (Default: present)

Für die Templates stehen eine Reihe Makros zur Verfügung, die die Konfiguration
etwas kompakter machen. Alle Makros sind für nginx und apache gleich.

### server() Makro

Das server-Makro erlaubt eine kompakte Definition von http- und https-Site.
Es wird wie folgt verwendet:

```
{% call server(server_names, http='yes', https='') %}
   < eigentliche Site-Konfiguration hier >
{% endcall %}
```

`server_names` ist die Liste der Servernamen, die konfiguriert werden sollen.
Der erste Name ist dabei der Hauptserver, alle weiteren sind Aliase.
ACHTUNG: `server_names` muss eine Liste sein.

'http' gibt an, wie Port 80 konfiguriert werden soll. `http='yes'` konfiguriert
http mit der angegebenen Site-Konfiguration. `http='forward'` konfiguriert eine
HTTP-Seite, die alles permanent auf HTTPS weiterleitet mit Ausnahme von
'.well-known/acme-challenge', welches zum Fossgis-ACME-Server verweist.

Wenn 'https' gesetzt ist, dann wird auch Port 443 mit der entsprechenden Site-
Konfiguration aufgesetzt. Dabei wird SSL aufgesetzt und das Zertifikat verwendet,
dass im `https`-Parameter angegeben wurde. (Siehe auch Zertifikat-Konfiguration
unten.

NGINX: server() nimmt in nginx_site noch einen zusätzlichen optionalen Parameter
       `listen_params`. Dieser wird verbatim an die listen-Direktive
       angehängt. Kann zum Beispiel benutzt werden, um eine Default-Site
       zu definieren.

### enable_ssl(cert) Makro

Das Makro fügt die entsprechenden Direktiven ein, die nötig sind, um SSL
aufzusetzen. Als Zertifikat werden dabei das im Parameter angegebene Zertifikat
benutzt.

### custom_log(name) Makro

Das Makro konfiguriert separate Log-Dateien in `<name>.access.log` und
`<name>.error.log`.

Zertifikat-Konfiguration
------------------------

Letsencrypt-Zertifikate werden durch den zentralen acme.openstreetmap.de-Server
verwaltet. Um so ein Zertifikat zu verwenden, müssen einfach in den Gruppen-
variablen der Rolle Einträge der folgenden Form vorgenommen werden:

```
my_role__acme_certificates:
    - name: my_role.web
      domains:
        - foo.de
        - web.com
      on_update:
        - systemctl reload nginx
```

Ein Zertifikat-Eintrag endet immer mit `__acme_certificates`. Was davor steht
ist egal, sollte aber im Allgemeinen der Rollenname sein, um Namenskonflikte
zu vermeiden. Der Eintrag enthält eine Liste von Zertifikaten mit folgenden
Parametern:

= name:      (string) Name des Zertifikats. Das eigentliche Zertifikat ist unter
             diesem Name dann im Verzeichnis `{{ acme__daemon_basedir }}/certs/`
             zu finden.
= domains:   Liste von Domains für die das Zertifikat ausgestellt werden soll.
- on_update: Liste von Befehlen, die ausgeführt werden sollen, nachdem ein neues
             Zertifikat auf der Zielmaschine installiert wurde. Die Befehle
             werden als root ausgeführt.

Für alle Zertifikate wird zuerst ein Snakeoil-Zertifikat installiert, so dass
Konfigurationen auf jeden Fall erst einmal funktionieren.

Die Rolle für den ACME-Server sammelt dann für alle Server ein, in welcher
Gruppe sie sind und welche Zertifikate für die Gruppe gebraucht werden. Es
wird dann für jede Server/Gruppenzertifikat-Kombination ein Zertifkat
angefordert. Der Einfachheit halber wird auch immer der interne Servername
mit ins Zertifikat genommen, damit man Sites auch direkt ansprechen kann.

ACHTUNG: Wenn ein neues Zertifikat konfiguriert wurde, muss das dem ACME-Server
bekannt gemacht werden via:

    ansible-playbook -l acme -i hosts.ini site.yml --tags certificates
