Passwortverwaltung in gopass
============================

Alle geheim zu haltenden strings, wie osm api oauth keys oder Datenbankpasswörter,
werden mit hilfe von gopass verschlüsselt und im separaten repo gopass_osmde
abgelegt. Die ansible skripte sollten aber so gefertigt sein, dass sie auch ohne
gopass durchlaufen.

Installation von gopass
-----------------------

Gopass selbst bietet eine Anleitung: https://github.com/gopasspw/gopass/blob/master/docs/setup.md#installation-steps
Für Debian gibts ein separates repo, unter Windows kann es über choco oder scoop, oder von hand heruntergeladen werden.

Einrichten von gopass
---------------------
Das fossgis osm-server gopass repository kann so eingerichtet werden:
```
gopass clone ssh://git@gitlab.fossgis.de:2224/osm-server/gopass_osmde.git gopass_osmde
```

Passwörter auflisten:
```
gopass ls
```

Neues geheimnis namens "bar" hinzufügen für rolle "foo":
```
gopass edit -c gopass_osmde/foo/bar
```

Verwendung in ansible erfolgt über ein lookup
```
{{ lookup ('gopass', 'gopass_osmde/foo/bar') }}
```



