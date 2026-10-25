# Tower Ascension – öffentliche Serverliste auf Render Free

Dieses Paket ist der kleine Vermittlungsdienst für die Internet-Serverliste.
Das Spiel selbst und seine Grafiken werden nicht hochgeladen. Der Host berechnet
die Partie weiterhin auf seinem Rechner. Es ist kein Relay und kein dedizierter Spielserver.

## 1. Server-Dateien auf GitHub hochladen

1. Auf GitHub anmelden und ein neues leeres Repository anlegen, zum Beispiel
   `tower-ascension-serverliste`. Öffentlich oder privat ist möglich, sofern Render Zugriff erhält.
2. **Add file → Upload files** wählen.
3. Die Dateien aus diesem Ordner hochladen: `app.py`, `requirements.txt`,
   `render.yaml`, `test_app.py`, `ANLEITUNG.md` und optional `.gitignore`.
4. Die Dateien sollen direkt im Repository liegen, nicht in einem zusätzlichen Unterordner.
5. Mit **Commit changes** speichern. Das komplette Spiel und insbesondere Probe nicht hochladen.

## 2. Kostenlosen Dienst bei Render erstellen

1. Bei https://dashboard.render.com anmelden.
2. **New → Web Service** wählen und das eben erstellte GitHub-Repository verbinden.
3. Folgende Werte eintragen:

| Feld | Wert |
| --- | --- |
| Name | z. B. `tower-ascension-serverliste` |
| Language / Runtime | Python 3 |
| Branch | `main`, sofern so angelegt |
| Root Directory | leer lassen |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn --workers 1 --threads 4 --bind 0.0.0.0:$PORT app:app` |
| Instance Type | **Free** |
| Health Check Path | `/health` |

4. Unter **Environment** diese Variablen anlegen:
   - `PYTHON_VERSION` = `3.12.10`
   - `TRUST_RENDER_PROXY` = `1`
5. **Deploy Web Service** wählen und warten, bis der Dienst **Live** meldet.
6. Die öffentliche HTTPS-Adresse kopieren, etwa `https://dein-name.onrender.com`.
7. Diese Adresse mit `/health` im Browser öffnen. Es muss JSON mit `"ok": true`
   erscheinen. Die Beispieladresse oben ist ein Platzhalter, kein fertiger Dienst.

Alternativ kann Render das enthaltene `render.yaml` über **New → Blueprint** lesen.
Auch dann muss das Paket direkt im Repository-Stamm liegen.

Wichtig: Genau **ein Worker und eine Instanz** verwenden. Die Liste liegt für den
Test im Arbeitsspeicher. Mehrere Worker würden unterschiedliche Listen führen.
Neustarts leeren die Liste; offene Hosts tragen sich automatisch erneut ein.
Eine Datenbank und ein gemeinsamer geheimer API-Schlüssel werden nicht benötigt.
Jede Lobby erhält automatisch einen eigenen geheimen Verwaltungsschlüssel.

## 3. Im Spiel verbinden

1. Die aktuelle Spielversion starten und **Spielen → Mehrspieler** öffnen.
2. Das Spiel verbindet sich automatisch mit
   `https://tower-ascension-serverliste.onrender.com`.
   Eine manuelle Eingabe der Adresse ist nicht mehr erforderlich.
3. Ein Spieler trägt seinen Namen ein, wählt Karte und Schwierigkeit und drückt
   **Spiel hosten**. Seine offene Lobby wird automatisch veröffentlicht.
4. Die anderen wählen den Eintrag mit **WEB** aus und drücken **Spiel beitreten**.
5. Sobald alle in der Lobby sind, startet der Host die Koop-Partie.

Der LAN-Browser funktioniert zusätzlich. Über das Filterfeld kann nach Hostname
oder Karte gesucht werden; rechts erscheinen Kartenvorschau und Details.
Ein späterer Wechsel des Internetdienstes erfolgt über den Standardwert
`DEFAULT_URL` in `scripts/public_directory.gd` des Spielprojekts.

## 4. Verbindung übers Internet

Die Serverliste findet Partien, stellt aber noch keinen Relay-Tunnel bereit.
Für den aktuellen direkten Internet-Test muss der Host:

- **UDP-Port 24567** im Router auf den eigenen Spielrechner weiterleiten;
- das Spiel in der Windows-Firewall für das verwendete Netzwerk zulassen;
- eine von außen erreichbare IPv4-Verbindung haben. Bei CGNAT/DS-Lite kann das
  trotz Portfreigabe scheitern. Dann ist eine spätere Relay-/NAT-Lösung erforderlich.

Die Mitspieler geben keine Host-IP ein: Sie kommt automatisch aus der Serverliste.
Render benötigt keine UDP-Portfreigabe; dort läuft nur der HTTPS-Listendienst.
Die Liste zeigt aktuell kompatible offene Lobbys mit freien Plätzen.

## Verhalten und Grenzen des kostenlosen Tests

- Render Free schläft nach 15 Minuten ohne eingehende Anfragen ein. Der erste
  Aufruf kann ungefähr eine Minute brauchen. Das Spiel wartet bis zu 90 Sekunden
  pro Anfrage und versucht es bei Fehlern erneut; LAN bleibt währenddessen verfügbar.
- Der Browser fragt ungefähr alle 8 Sekunden an. Hosts erneuern ihren Eintrag
  spätestens alle 15 Sekunden, bei Änderungen früher.
- Beim Starten/Verlassen wird die Lobby abgemeldet. Nach Absturz verschwindet sie
  spätestens nach 65 Sekunden auf dem Dienst, plus dem nächsten Browser-Abruf.
- Die öffentliche Liste enthält Hostname, öffentliche Verbindungsadresse, Port,
  Karte, Schwierigkeit und Spielerzahl. Es werden keine Spielstände hochgeladen.
- Maximal 256 offene Einträge und 8 je Quelladresse; Mengen- und Eingabegrenzen
  sowie getrennte Verwaltungs-Token schützen den kleinen Testdienst.
- Es handelt sich um einen Testdienst ohne Konten, Moderationssystem oder garantierte Verfügbarkeit.

## Lokal prüfen (optional)

Im Ordner mit Python 3.12:

```text
python -m unittest -v test_app.py
python app.py
```

Danach lautet die lokale Testadresse `http://127.0.0.1:8765`.
Der eingebaute Python-Testserver ist nur für lokale Tests. Auf Render Gunicorn nutzen.

Offizielle Anleitungen:
- https://render.com/docs/web-services
- https://render.com/docs/deploy-flask (beschreibt ebenfalls Python + Gunicorn)
- https://render.com/docs/free
- https://render.com/docs/health-checks
