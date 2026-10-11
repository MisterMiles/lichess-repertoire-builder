# Ausführliche Anleitung

[Kurzfassung](../README.de.md) | [English](GUIDE.md)

Hier steht jede Option. Für den schnellen Einstieg reicht die [README](../README.de.md).

Baut für Weiß oder Schwarz ein kommentiertes Repertoire als PGN: die häufigsten Antworten des Gegners, wie diese Partien ausgehen, wie Stockfish die Stellungen bewertet, wo der Gegner am häufigsten Fehler macht und welche Bauernstrukturen typisch sind. Dazu kommt eine kleine Quickstart PGN mit den wahrscheinlichsten Linien zum Üben.

## Voraussetzungen

Immer nötig:
- **Python 3** mit dem Paket `chess` (python-chess). Getestet mit 3.13, ab 3.9 sollte es laufen.
- **Stockfish**. Name oder voller Pfad steht in der Konfiguration unter `"stockfish"`.
- **Für das Filterskript:** `bash`, `awk` (`mawk` ist deutlich schneller, das Skript nimmt automatisch das schnellste vorhandene), `zstd`, `curl` für `-m`, optional `pv` für die Fortschrittsanzeige.
- **Speicherplatz:** Eine Monatsdatei hat etwa 29 GB. Mit `-m` wird gestreamt und nichts gespeichert. `repertoire.sh` streamt ebenfalls, außer mit `--archiv`.
- **Arbeitsspeicher:** Alle gefilterten Partien werden auf einmal geladen. Noch nicht gemessen, sehr große Datensätze können viel RAM brauchen.

### macOS

```bash
brew install zstd pv mawk stockfish
python3 -m venv ~/.venv-repertoire
~/.venv-repertoire/bin/pip install chess
```

Auch das Python von Homebrew lässt `pip install` direkt ins System nicht zu, deshalb die virtuelle Umgebung. Gestartet wird dann mit `~/.venv-repertoire/bin/python repertoire.py ...`.

### Linux (Debian, Ubuntu)

```bash
sudo apt install zstd pv mawk stockfish python3-venv
python3 -m venv ~/.venv-repertoire
~/.venv-repertoire/bin/pip install chess
```

Neuere Distributionen lassen `pip install` direkt ins System nicht zu, deshalb die virtuelle Umgebung. Gestartet wird dann mit `~/.venv-repertoire/bin/python repertoire.py ...`. Das Stockfish Paket der Distribution ist oft älter, aktuelle Versionen gibt es unter https://stockfishchess.org/download/.

### Was getestet ist

| | Filterskript | repertoire.py |
|---|---|---|
| Linux | getestet | getestet (Python 3.13) |
| macOS | getestet | getestet |

Quellen:
- Lichess Open Database: https://database.lichess.org
- Lichess Elite Database (2500+ gegen 2300+): https://database.nikonoel.fr
- Stockfish: https://github.com/official-stockfish/Stockfish
- python-chess: https://github.com/niklasf/python-chess
- zstd: https://github.com/facebook/zstd, pv: https://www.ivarch.com/programs/pv.shtml, mawk: https://invisible-island.net/mawk/

## Alles mit einem Befehl: repertoire.sh

`repertoire.sh` erledigt alle Schritte unten auf einmal: Python Umgebung einrichten, Partien streamen und filtern, `konfiguration.json` anlegen und das Repertoire bauen. Alles landet in einem Ordner.

```bash
bash repertoire.sh weiss "1. e4"
bash repertoire.sh schwarz "1. d4 d5" --elo 1600-2000 --schnell
```

| Option | Bedeutung | Standard |
|---|---|---|
| `--elo VON-BIS` | Elo Bereich beider Spieler | 1800-2499 |
| `--monat JJJJ-MM` | Lichess Monat, mehrere als `JJJJ-MM..JJJJ-MM` | letzter voller Monat |
| `--monate N` | die letzten N vollen Monate | aus |
| `--archiv ORDNER` | Monatsdateien dort speichern statt nur streamen (je etwa 29 GB), vorhandene werden wiederverwendet | aus |
| `--datei DATEI` | eigene Lichess Datei (`.pgn` oder `.pgn.zst`) statt Download | aus |
| `--name NAME` | Ordnername für die Ergebnisse | aus Farbe und Zügen |
| `--repertoire PGN` | eigenes Repertoire, dessen Züge markiert werden | keins |
| `--schnell` | schneller Probelauf mit geringer Stockfish Tiefe | aus |

Ein erneuter Aufruf mit gleichen Angaben nutzt die schon geladenen Partien und Stockfish Ergebnisse. Für Feineinstellungen `konfiguration.json` im Ordner bearbeiten (Felder siehe unten) und erneut starten.

Die folgenden Abschnitte beschreiben die einzelnen Schritte für volle Kontrolle.

## 1. Partien filtern

Monatsdatei laden (etwa 29 GB) oder direkt streamen, dann nach Startzügen filtern. Züge werden in englischer Notation angegeben.

```bash
# lokale Datei
bash lichess_filter.sh -s "1. e4" -i lichess_db_standard_rated_2026-09.pgn.zst -o partien.pgn --tsv partien.tsv

# direkt von Lichess streamen, nichts Großes wird gespeichert
bash lichess_filter.sh -s "1. d4 d5 2. c4" -m 2026-09 -o partien.pgn --tsv partien.tsv
```

| Option | Bedeutung | Standard |
|---|---|---|
| `-s` | Startzüge, z. B. `"1. e4 c5 2. Nf3"` | Pflicht, außer bei `--enthaelt` |
| `-i` / `-m` | Datei (`.pgn.zst` oder `.pgn`) oder Monat `JJJJ-MM` | eins davon |
| `-o` | Ausgabe PGN | Pflicht |
| `--tsv` | zusätzlich Tabelle für `repertoire.py` | aus |
| `--elo-min` / `--elo-max` | beide Spieler in diesem Bereich | 1800 / 2499 |
| `--elo-einer` | mindestens ein Spieler ab diesem Wert | aus |
| `--mit-bullet`, `--mit-bots` | Bullet oder Bot Partien behalten | ohne |
| `--halbzuege` | Halbzüge in der Tabelle | 30 |
| `--enthaelt` | ein Zug, der irgendwo in den ersten Zügen vorkommt (für Zugumstellungen) | aus |
| `--zug-farbe` | wer diesen Zug spielt, `weiss` oder `schwarz` | weiss |
| `--bis-zug` | spätestens in diesem Zug | 5 |
| `--nicht-start` | Partien mit diesem Anfang ausschließen | aus |

Bei Schwarz gehören der erste Zug von Weiß und die eigene Antwort in die Startzüge, z. B. `"1. d4 d5"`. Sonst wählt das Skript als Hauptvariante die meistgespielte Antwort, und die muss nicht die eigene sein.

Ein Monat dauert je nach Rechner und Startzügen etwa 5 bis 15 Minuten. Mehrere Monate: Befehl je Monat ausführen und die Tabellen mit `cat` zusammenfügen. `repertoire.sh` macht das mit `--monate` oder `--monat VON..BIS` automatisch und merkt sich jeden fertigen Monat im Unterordner `monate`.

## 2. Konfiguration anlegen

Eine JSON Datei je Repertoire, Vorlagen: `beispiel_weiss.json`, `beispiel_schwarz.json`. Nur die Felder angeben, die vom Standard abweichen.

| Feld | Bedeutung | Standard |
|---|---|---|
| `titel`, `farbe`, `start`, `daten`, `ausgabe` | Name, `"weiss"` oder `"schwarz"`, Startzüge, Tabelle aus Schritt 1, Name der PGN | Pflicht |
| `system` | woran eine Partie als eigenes System zählt, z. B. `[{"zug": "Nf3", "spaetestens_zug": 3, "nicht_vorher": []}]` | alle Partien |
| `ohne_systemfilter` | erste Antworten des Gegners, die ohne Systemregel gezählt werden (z. B. ein Gambit) | keine |
| `erste_antworten` | Anzahl der ersten Antworten des Gegners | 10 |
| `antworten` | Antworten des Gegners je Zug | 3 |
| `fruehe_zuege_ab_5_prozent` | Zugnummern, in denen zusätzlich jede Antwort ab 5 % kommt | 2 und 3 |
| `min_partien` | Linie verzweigt nur ab so vielen Partien | 20 |
| `bis_zug` | maximale Tiefe | 15 |
| `hv_tiefe` | Zug des Gegners, an dem die Hauptvariante in Kapitel geteilt wird | 4 |
| `kapitel_max` | größere Kapitel werden geteilt | 800 Züge |
| `kapitel_min_anteil` | Kapitel, die weniger Partien (in % aller) erreichen, werden je Verzweigung zusammengelegt und ans Ende gestellt | 2 |
| `kapitel_min_zug`, `verlaengern_min_partien` | die Hauptvariante jedes Kapitels läuft mindestens bis zu diesem Zug: erst die meistgespielten Züge, solange so viele Partien übrig sind, dann Stockfish | 12, 5 |
| `repertoire_pgn` | bestehendes Repertoire, eigene Züge daraus werden als Repertoirezug markiert, Kommentare übernommen | keins |
| `repertoire_zuege` | `"alle"`: jeder eigene Zug der Datei gilt als Repertoirezug, `"hauptzug"`: nur der jeweils erste | alle |
| `kommentare_entfernen` | reguläre Ausdrücke für Sätze, die aus diesen Kommentaren entfallen | keine |
| `anhang_pgn` | PGN Dateien, deren Partien als Themenkapitel angehängt werden | keine |
| `statistik` | Anteil und Partienzahl an jeden Zug schreiben | aus |
| `quickstart_linien`, `quickstart_bis_zug` | Zahl und Länge der Linien in der Quickstart PGN | 15, Zug 14 |
| `fehler` | häufige Fehler des Gegners je Kapitel suchen | an |
| `fehler_grenze` | Verlust auf der Gewinnchancen Skala, ab dem ein Zug als Fehler zählt (0,2 ist die Lichess Grenze für „Fehler“, in ausgeglichenen Stellungen etwa ein Bauer) | 0,2 |
| `fehler_min_partien`, `fehler_min_anteil`, `fehler_anzahl` | ein Zug wird nur geprüft ab so vielen Partien und so viel Prozent, gezeigt werden die häufigsten | 10, 5 %, 5 |
| `plan_zuege`, `plan_min_partien` | eigene Züge, die am Linienende als typischer Aufbau aus der Praxis gezeigt werden, und die Mindestzahl an Partien dafür | 3, 5 |
| `strukturen_zug`, `strukturen_anzahl` | Zeitpunkt und Zahl der Bauernstrukturen | Zug 12, 5 |
| `strukturen_text` | JSON Datei mit eigenen Erklärungen je Struktur (`{"id": "Text"}`, die ids stehen in `<ausgabe>_strukturen.json`) | keine |
| `stockfish`, `tiefe`, `fehler_tiefe`, `prozesse` | Pfad zur Engine, Suchtiefe am Linienende und bei der Fehlersuche, parallele Prozesse | stockfish, 18, 14, 2 |
| `eco` | ECO für die Kopfzeilen | ? |

## 3. Repertoire bauen

```bash
python3 repertoire.py meine_konfiguration.json
```

Ausgaben:
- `<ausgabe>.pgn`: das Repertoire
- `<ausgabe>_quickstart.pgn`: die wahrscheinlichsten Linien bis Zug 14, je Linie ein Kapitel. Wo die Daten enden, geht es mit dem besten Zug von Stockfish weiter, das steht als Kommentar an der Stelle.
- `<ausgabe>_strukturen.json`: die Bauernstrukturen mit allen Zahlen, Grundlage für eigene Erklärungstexte
- `<ausgabe>_stockfish.json`: Zwischenspeicher der Engine

### Laufzeit und Fortschritt

Das Skript arbeitet in sechs Schritten und zeigt bei den langen Schritten einen Balken mit Prozent, Anzahl und geschätzter Restzeit:

```
1/6 Daten
  Partien laden [██████████░░░░░░░░░░]  52,0 %  97456/187412  noch ca. 4 Min.
3/6 Stockfish
  Stockfish     [████░░░░░░░░░░░░░░░░]  21,3 %  560/2613  noch ca. 38 Min.
```

Richtwerte für etwa 190.000 Partien auf einem Rechner mit 2 Prozessen: Daten laden 10 Minuten, Stockfish 30 bis 90 Minuten (der größte Teil, abhängig von `tiefe`, `fehler_tiefe` und der Zahl der Linien), Musterpartien 5 Minuten, Schreiben unter einer Minute. Mehr `prozesse` beschleunigen Stockfish fast linear, sinnvoll ist die Zahl der CPU Kerne minus eins. Abbrechen ist kein Problem: Die Stockfish Ergebnisse werden laufend gespeichert, ein neuer Lauf rechnet nur, was noch fehlt.

## Aufbau der Repertoire PGN

- 01 Intro mit Regeln und Symbolerklärung, dazu die Hauptvariante.
- Die Kapitel sind danach sortiert, wie oft du sie in der Praxis bekommst, das wahrscheinlichste zuerst. Kapitel unter 2 % werden je Verzweigung als „Seltene Abweichungen“ am Ende zusammengefasst.
- Die Hauptvariante jedes Kapitels läuft mindestens bis Zug 12: erst die meistgespielten Züge, solange mindestens 5 Partien übrig sind, danach die besten Züge laut Stockfish (per Kommentar markiert). Endet sie in einer Zugumstellung, geht es mit der Hauptvariante von dort weiter.
- Im Kapitelnamen steht, wie viel Prozent aller ausgewerteten Partien das Kapitel erreichen, z. B. `(4,2 % gesamt)`.
- Hauptvariante ist der meistgespielte Zug, der eigene Repertoirezug steht markiert daneben.
- Am Linienende: Bewertungszeichen von Stockfish, Musterpartie mit dem höchsten Elo Schnitt und blaue Pfeile für den typischen Aufbau aus der Praxis: die nächsten 3 eigenen Züge (ohne Schlagzüge), mit denen deine Seite nach dieser Stellung am besten gepunktet hat, ab 5 Partien. Bei weniger Partien zeigt ein grüner Pfeil stattdessen den besten Zug laut Stockfish.
- Am Ende jedes Kapitels: die häufigsten Fehler des Gegners. Ein Zug zählt als Fehler, wenn er laut Stockfish mindestens `fehler_grenze` Gewinnchancen kostet. Zu jedem Fehler stehen die Bewertung vorher und nachher und die Erfolgsquote nach diesem Zug im Vergleich zu den übrigen Zügen derselben Stellung. Im Baum ist der Zug mit ? oder ?? markiert, dazu die Widerlegung.
- Bauernstrukturen: die häufigsten Zentrumsstrukturen (Linien c bis f) nach Zug 12, je ein Kapitel mit Beispielstellung. Bekannte Strukturen werden benannt (z. B. Stonewall, Carlsbad, isolierter Damenbauer, Französisch, Königsindisch) und bekommen die Standardpläne dazu. Merkmale der Beispielstellung werden automatisch beschrieben (isolierte, doppelte und freie Bauern, offene und halboffene Linien, Vorposten für Springer). Auf dem Brett markieren gelbe Felder die typischen Felder deiner Leichtfiguren, Pfeile zeigen die häufigsten Bauernhebel (grün deine, rot die des Gegners), die Hebel der Seite am Zug lassen sich als Variante durchklicken.
- Anhang mit Themenkapiteln, am Ende eine Zusammenfassung bis Zug 5.
- Zugumstellungen verweisen auf das Kapitel, in dem die Stellung zuerst vorkommt.

## Zugumstellungen über andere Zugfolgen messen

Das Repertoire zählt nur Partien, die mit den Startzügen beginnen. Wie viele Partien über eine andere Zugfolge in dieselben Stellungen kommen, misst `zugumstellungen.py`:

```bash
# Partien, in denen der eigene Schlüsselzug erst später kommt
bash lichess_filter.sh --enthaelt d4 --bis-zug 4 --nicht-start "1. d4" -i monat.pgn.zst -o andere.pgn --tsv andere.tsv
python3 zugumstellungen.py meine_konfiguration.json andere.tsv
```

Das Ergebnis zeigt, wie viele zusätzliche Partien eine Stellung des Repertoires erreichen und über welche Zugfolgen.

## Lizenz

GPL 3.0, passend zu python-chess und Stockfish. Siehe [LICENSE](../LICENSE).
