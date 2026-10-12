![lichess repertoire builder](docs/banner.svg)

# lichess repertoire builder

[English](README.md) | **Deutsch**

Du sagst, welche Eröffnung du spielst. Das Werkzeug holt sich dazu echte Lichess Partien aus deinem Elo Bereich und baut daraus ein Repertoire als PGN: was deine Gegner wirklich spielen, wie die Partien ausgehen, wo sie am häufigsten Fehler machen und wie Stockfish die Stellungen sieht. Die PGN öffnest du in einer Lichess Studie oder in ChessBase.

## Die Idee dahinter

Ein Repertoire aus dem Buch sagt dir, was in der Theorie am besten ist. Dieses Werkzeug sagt dir, was dir auf deinem Niveau wirklich begegnet und wie du darauf reagierst.

- **Erst die Praxis, dann die Engine.** Die Partien bestimmen, was ins Repertoire kommt und in welcher Reihenfolge: je häufiger eine Linie in deinem Elo Bereich vorkommt, desto früher steht sie da. Stockfish prüft und korrigiert, er wählt nicht die Themen.
- **Stellungen statt Zugfolgen.** Verschiedene Zugfolgen, die zur selben Stellung führen, werden zusammengezählt. Eine Linie zerfällt so nicht in viele kleine, die selten aussehen.
- **Fehler, die wirklich passieren.** Zu jeder Stellung siehst du, welche Fehler deine Gegner tatsächlich machen, wie oft, und was sie bestraft. Ein Fehler ist ein Zug, der laut Stockfish einen deutlichen Teil der Gewinnchancen kostet.
- **Pläne, nicht nur Züge.** Jede Linie endet mit einer Musterpartie, dem typischen Aufbau, der in der Praxis am besten gepunktet hat (blaue Pfeile), und der Bauernstruktur, auf die du zusteuerst.
- **Einmal sammeln, beliebig oft auswerten.** Der langsame Teil sind die Rohdaten. Sie werden einmal zu einer Partienbank. Jedes weitere Repertoire, ob andere Startzüge, andere Farbe oder anderer Elo Bereich, durchsucht nur noch die Bank. Auch die Stockfish Ergebnisse werden zwischengespeichert, ein zweiter Lauf rechnet nur Neues.

## Schnellstart (Mac)

**1. Programme installieren** (einmalig, im Programm Terminal). Falls Homebrew fehlt, zuerst die Zeile von [brew.sh](https://brew.sh) ausführen.

```bash
brew install python zstd pv mawk stockfish
```

**2. Werkzeug herunterladen**

```bash
git clone https://github.com/MisterMiles/lichess-repertoire-builder.git
cd lichess-repertoire-builder
```

Ohne git: oben auf GitHub „Code“ und dann „Download ZIP“ wählen, entpacken und im Terminal mit `cd` in den Ordner wechseln.

**3. Repertoire bauen**

```bash
bash repertoire.sh white "1. e4"
```

Fertig. Beim ersten Mal richtet das Skript alles Nötige selbst ein.

## Beispiele

```bash
# Weiß mit 1.e4, gegen alles, was Schwarz spielt
bash repertoire.sh white "1. e4"

# Schwarz gegen 1.d4 mit 1...d5, Gegner zwischen 1600 und 2000, zuerst als schneller Probelauf
bash repertoire.sh black "1. d4 d5" --elo 1600-2000 --quick

# Mehr Partien: die letzten drei Monate statt nur einem
bash repertoire.sh white "1. e4" --months 3
```

Farbe ist `white` oder `black`, Optionen sind englisch. Die deutschen Namen von früher (`weiss`, `schwarz`, `--monat`, `--schnell` und so weiter) funktionieren weiter. Züge schreibst du in englischer Notation: N Springer, B Läufer, R Turm, Q Dame, K König. Bei Schwarz gehört deine eigene Antwort mit in die Startzüge. Auch die PGN nutzt englische Notation, mit `--notation de` stehen Kapitelnamen und Kommentare mit deutschen Figuren (S, L, T, D).

## Was du bekommst

Die Ergebnisse landen im Ordner `repertoires` neben dem Tool Ordner (änderbar mit `--out ORDNER`):
- **`….pgn`**: dein Repertoire, ein Kapitel je Linie, sortiert danach, wie oft du sie in der Praxis bekommst (der Anteil steht im Kapitelnamen). Die Hauptvariante jedes Kapitels läuft mindestens bis Zug 15, seltene Linien stehen gebündelt am Ende. Am Linienende stehen Stockfish Bewertung, eine Musterpartie und blaue Pfeile für den Aufbau, der in der Praxis am besten gepunktet hat, am Kapitelende die häufigsten Fehler deiner Gegner samt Widerlegung. Dazu kommen die typischen Bauernstrukturen.
- **`…_quickstart.pgn`**: die 15 wahrscheinlichsten Linien bis Zug 14, ideal zum Üben.

Partien, Stockfish Zwischenspeicher und `konfiguration.json` bleiben in `repertoires/arbeit/NAME`, der Tool Ordner bleibt sauber.

## So arbeitest du am besten damit

1. **Die Idee günstig prüfen.** Starte zuerst mit `--quick`. Nach wenigen Minuten siehst du, ob Startzüge und Elo Bereich einen sinnvollen Baum ergeben. Falsche Startzüge fallen auf, bevor etwas heruntergeladen wird.
2. **Der erste volle Lauf baut die Partienbank.** Hänge `--months 3 --bank ORDNER --archive ORDNER --delete-archive` an und lass `--quick` weg. Jede 29 GB Monatsdatei wird gelöscht, sobald ihre Tabelle fertig ist, übrig bleibt nur die kompakte Bank.
3. **In der richtigen Reihenfolge lesen.** Öffne zuerst die Quickstart Datei, sie enthält die 15 wahrscheinlichsten Linien. Die Hauptdatei ist das Nachschlagewerk, zu dem du zurückkehrst.
4. **In kleinen Schritten lernen.** Importiere die PGN in eine Lichess Studie und lerne die Kapitel von oben nach unten. Die Reihenfolge ist schon die Reihenfolge der Wichtigkeit.
5. **Anpassen und neu laufen lassen.** Einstellungen wie die Mindestzahl an Partien je Linie oder die Tiefe der Hauptvarianten stehen in der `konfiguration.json` im Arbeitsordner. Ein neuer Lauf nutzt Partien und Engine Ergebnisse wieder.
6. **Das eigene Repertoire dazunehmen.** Mit `--repertoire PGN` werden deine eigenen Züge markiert, so siehst du, wo Praxis und deine Vorbereitung auseinanderliegen.
7. **Ab und zu auffrischen.** Neue Monate kommen in dieselbe Bank und verändern die Zahlen nur leicht.

Behalte im Kopf, was die Zahlen sind: Statistik von Onlinepartien in deinem Elo Bereich, ohne Bullet und Bots. Linien mit wenigen Partien sind unsicher, Stockfish Bewertungen entstehen bei fester Tiefe, und die Musterpartie ist ein Beispiel, kein Beweis. Das Repertoire ist ein gut sortierter Ausgangspunkt für dein eigenes Urteil.

## Gut zu wissen

- **Dauer:** Die Partien eines Lichess Monats werden aus dem Internet gestreamt (etwa 29 GB, nichts davon wird gespeichert). Das dauert je nach Leitung 30 Minuten bis einige Stunden. Danach rechnet Stockfish 15 bis 60 Minuten. Mit `--quick` siehst du das Ergebnis in wenigen Minuten, sobald die Partien da sind.
- **Mehr Partien:** `--months 3` nimmt die letzten drei vollen Monate, `--month 2026-07..2026-09` einen festen Zeitraum. Jeder Monat wird einzeln geladen und gefiltert, die Wartezeit wächst also mit. Mit `--archive ORDNER` bleiben die Monatsdateien gespeichert (je etwa 29 GB) und werden beim nächsten Mal nicht neu geladen.
- **Mehrere Analysen:** Mit `--bank ORDNER` wird jeder Monat einmal in eine Partienbank umgewandelt, eine kompakte Tabelle aller Partien (etwa 5 GB pro Monat). Danach braucht jede weitere Analyse mit anderen Startzügen, anderer Farbe oder anderem Elo Bereich nur noch Sekunden pro Monat, bevor Stockfish startet. Beispiel: `bash repertoire.sh white "1. e4" --months 3 --bank ~/gamebank`. Ein Monat, der in der Bank ist, wird nie neu gebaut, und mit `--archive` plus `--delete-archive` wird die 29 GB Monatsdatei gelöscht, sobald ihre Banktabelle fertig ist.
- **Beim Warten:** Bei jedem Schritt hüpft ein Springer über ein kleines Brett, dazu Prozent und Restzeit. `--plain` schaltet das ab.
- **Nochmal starten:** Mit den gleichen Angaben nutzt das Skript die schon geladenen Partien und rechnet nur, was fehlt.
- **Linux:** Statt Homebrew `sudo apt install python3-venv zstd pv mawk stockfish`, der Rest ist gleich.
- **Mehr Einstellungen:** Elo, Monat, eigenes Repertoire und alle Feineinstellungen stehen in der [ausführlichen Anleitung](docs/ANLEITUNG.md).

## Lizenz

GPL 3.0, siehe [LICENSE](LICENSE). Daten: [Lichess Open Database](https://database.lichess.org), Engine: [Stockfish](https://stockfishchess.org).
