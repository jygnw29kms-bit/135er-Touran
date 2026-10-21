# Website dezender.de/touran

`index.html` und `assets/` bilden eine eigenständige, responsive deutsche Projektseite. Keine externen Fonts, Tracker oder JavaScript-Bibliotheken. Die Galerie öffnet Bilder im Tastatur-bedienbaren Dialog. Downloadinformationen werden gegen das vorhandene `update.json` abgeglichen.

Das große Titelbild ist das vom Eigentümer hochgeladene `splash_logo_001.bmp`, unverändert und verlustfrei für den Browser als `assets/135er-touran.webp` gespeichert. Das vorhandene App-Icon bleibt das Favicon. Die drei SVG-Ansichten sind ausdrücklich gekennzeichnete Nachbildungen des App-Entwicklungsstands 0.7.1; keine Screenshots und keine simulierten Fahrzeugmessungen. Die vorhandene `touran_master_final.webp` ist nicht als Bild dekodierbar, auch nicht im gebauten APK. Das Eigentümermotiv ist jetzt vorhanden; echte Radio-Screenshots sind noch nicht verfügbar.

## Bereitstellung

Nachtrag 21.10.2026: `.github/workflows/deploy-touran-api.yml` stellt inzwischen einen GitHub-Deploymentweg für **den Upload-Endpunkt** bereit. Er veröffentlicht nicht die Website oder die APK. Sein letzter geprüfter Lauf für `b6bd252` scheiterte im SSH-/SCP-Schritt. Der Workflow nennt `/var/www/vhosts/dezender.de/httpdocs/touran` als Ziel und verwendet GitHub-Secrets; ihre tatsächliche Serverberechtigung ist damit nicht nachgewiesen. Die Datei `/srv/touranradio/upload/inbox` aus einer früheren Sitzung ist kein Webroot.

1. Tatsächlichen Webroot für `/touran/` bestimmen und die bisherige `index.html` sichern.
2. `assets/` hochladen und Bild-/CSS-/JS-Abrufe prüfen.
3. `index.html` zuletzt ersetzen, anschließend öffentliche Seite auf Desktop und Mobilgerät prüfen.
4. Bei Problemen die gesicherte `index.html` zurückspielen.

Nur die Website-Dateien veröffentlichen. `api/`, `logs/`, Inbox, APK und `update.json` nicht ersetzen: die öffentliche APK ist laut abgerufenem Manifest weiterhin 0.6.1. Die Veröffentlichung von 0.7.1 benötigt einen getrennten konsistenten APK-/Signatur-/Manifest-Schritt.

Lokale Vorschau:

```sh
python3 -m http.server 8080 --directory server
```

`http://localhost:8080` öffnen. Die statische Downloadinformation bleibt auch ohne HTTPS erreichbar; die serverseitige Paket-URL wird bei einem gültigen Manifest übernommen.

## Veröffentlichung über Plesk

1. Plesk öffnen → **Websites & Domains → dezender.de**. Unter den Hosting-Einstellungen den tatsächlichen Dokumentenstamm prüfen; `httpdocs` ist häufig, aber nicht garantiert.
2. **Dateien / File Manager** öffnen und innerhalb des Dokumentenstamms den Ordner `touran` aufrufen. Vorhandene `index.html` herunterladen oder außerhalb des öffentlich erreichbaren Webroots sichern.
3. Das Website-ZIP auf dem eigenen Rechner entpacken. Den enthaltenen Ordner `assets` in `touran` hochladen; vorhandene gleichnamige Website-Assets ersetzen. Danach die neue `index.html` hochladen. `WEBSITE.md` ist eine lokale Anleitung und muss nicht veröffentlicht werden.
4. `https://dezender.de/touran/` und `https://dezender.de/touran/assets/135er-touran.webp` prüfen, gegebenenfalls Browsercache mit Strg+F5 neu laden.
5. APK-Link, Galerie und Mobilansicht prüfen. Upload-API, Logs und `update.json` bleiben beim Austausch dieser Website-Dateien erhalten.

Alternativ unterstützt Plesk bei installierter Git-Erweiterung eine Repository-Bereitstellung. Dafür muss das Bereitstellungsziel zur bestehenden Website passen; nicht das komplette Projekt in den Webroot ausrollen. Eine angemeldete Plesk-Verbindung oder eine Plesk-Git-Bereitstellung ist in dieser Sitzung nicht verfügbar. Der vorhandene GitHub-API-Workflow ist davon getrennt.
