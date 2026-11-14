![lichess repertoire builder](docs/banner.svg)

# lichess repertoire builder

[English](README.md) | **Deutsch**

Du sagst, welche Eröffnung du spielst. Das Werkzeug nimmt echte Lichess Partien aus deinem Elo Bereich und baut daraus ein Repertoire als PGN: was deine Gegner wirklich spielen, wo sie am häufigsten Fehler machen und wie Stockfish die Stellungen sieht. Die PGN öffnest du in einer Lichess Studie oder in ChessBase.

[Schnellstart](#schnellstart-mac) · [Die Idee](#die-idee-dahinter) · [Partienbank](#die-partienbank) · [So arbeitest du damit](#so-arbeitest-du-am-besten-damit) · [Optionen](#optionen) · [Gut zu wissen](#gut-zu-wissen)

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

```bash
# Schwarz gegen 1.d4 mit 1...d5, Gegner mit Elo 1600 bis 2000, erst ein schneller Probelauf
bash repertoire.sh black "1. d4 d5" --elo 1600-2000 --quick
```

Der erste volle Lauf lädt jeden Monat einmal herunter (etwa 29 GB, dauert Stunden), mit mehreren Verbindungen. Bei einem Abbruch startest du denselben Befehl noch einmal, dann geht es dort weiter. Jeder Monat wird zu einer Partienbank Tabelle in `~/lichess-data/bank`, spätere Repertoires überspringen den Download:

```bash
bash repertoire.sh white "1. e4" --months 3
```

## Was du bekommst

Die Ergebnisse landen im Ordner `repertoires` neben dem Tool Ordner (mit `--out` änderbar).

| Datei | Inhalt |
| --- | --- |
| `NAME.pgn` | Dein Repertoire, ein Kapitel je Linie, sortiert danach, wie oft du sie bekommst. Die Hauptvarianten laufen mindestens bis Zug 15, seltene Linien stehen gebündelt am Ende. |
| `NAME_quickstart.pgn` | Die 15 wahrscheinlichsten Linien bis Zug 14, zum Üben. |
| `NAME_strukturen.json` | Die typischen Bauernstrukturen mit allen Zahlen. |

Am Linienende stehen Stockfish Bewertung, eine Musterpartie und blaue Pfeile für den Aufbau, der in der Praxis am besten gepunktet hat. Am Kapitelende stehen die häufigsten Fehler deiner Gegner samt Widerlegung. Partien, Zwischenspeicher der Engine und `konfiguration.json` bleiben in `repertoires/arbeit/NAME`.

## Die Idee dahinter

Ein Repertoire aus dem Buch sagt dir, was in der Theorie am besten ist. Dieses Werkzeug sagt dir, was dir auf deinem Niveau wirklich begegnet. Die Partien entscheiden, was hineinkommt und in welcher Reihenfolge, Stockfish prüft und korrigiert nur. Verschiedene Zugfolgen, die in dieselbe Stellung führen, werden zusammengezählt. Zu jeder Stellung siehst du, welche Fehler deine Gegner wirklich machen und was sie widerlegt. Der langsame Teil sind die Rohdaten: Sie werden einmal zur Partienbank, und jedes weitere Repertoire durchsucht nur noch die Bank.

## Die Partienbank

Ein Lichess Monat ist eine PGN von etwa 29 GB (komprimiert). Für ein Repertoire brauchst du nur einen kleinen Teil jeder Partie. Die Bank behält deshalb eine mit zstd komprimierte Zeile pro Partie: den Link zur Partie, die Spielernamen, beide Elo Zahlen, Ergebnis und Art des Endes, Bedenkzeit und Datum, Partielänge, letzten Zug und die ersten 40 Halbzüge. Es fehlen Uhrzeiten, Engine Bewertungen, Elo Änderungen, Eröffnungsnamen, Kommentare und die Züge zwischen dem 40. Halbzug und dem letzten. Bullet Partien, Bot Partien und Partien ohne Elo oder Ergebnis sind gar nicht erst drin.

Ein Monat schrumpft auf etwa 5 GB (Schätzung von einer 2 GB Probe), und die Suche nach deinen Startzügen dauert unter einer Minute statt etwa 8 (Schätzung). Eine Bank enthält alle Eröffnungen, Farben und Elo Bereiche und reicht für beliebig viele Repertoires.

Der Preis: Die Partien sind nur bis zum 20. Zug bekannt (keine Endspielstudien), und Bullet fehlt. Für Bullet baust du aus dem Original eine zweite Bank mit `bash gamebank.sh 2026-09 --data NEUERORDNER --keep-raw --with-bullet`. Behalte die Monatsdateien mit `--keep-raw`, bis du sicher bist, dass du sie nicht brauchst.

## So arbeitest du am besten damit

1. Starte zuerst mit `--quick`. Falsche Startzüge fallen auf, bevor etwas heruntergeladen wird.
2. Der erste volle Lauf baut die Partienbank: Hänge `--months 3` an und lass `--quick` weg. Jede Monatsdatei wird gelöscht, sobald ihre Tabelle fertig ist (`--rohdaten-behalten` behält sie).
3. Lies zuerst die Quickstart Datei, dann die Hauptdatei als Nachschlagewerk. Importiere die PGN in eine Lichess Studie und lerne von oben nach unten, denn die Reihenfolge ist die Reihenfolge der Wichtigkeit.
4. Die Einstellungen stehen in `konfiguration.json` im Arbeitsordner, ein neuer Lauf nutzt Partien und Engine Ergebnisse wieder. Mit `--repertoire PGN` werden deine eigenen Züge markiert.
5. Neue Monate kommen in dieselbe Bank.

Die Zahlen sind Statistik von Onlinepartien in deinem Elo Bereich, ohne Bullet und Bots. Linien mit wenigen Partien sind unsicher, Bewertungen entstehen bei fester Tiefe, und die Musterpartie ist ein Beispiel, kein Beweis.

## Optionen

| Option | Bedeutung | Standard |
| --- | --- | --- |
| `--elo VON-BIS` | Elo Bereich beider Spieler | 1800-2499 |
| `--month JJJJ-MM` / `--month A..B` | Ein Monat oder ein Bereich | letzter voller Monat |
| `--months N` | Die letzten N vollen Monate | aus |
| `--data ORDNER` | Wo Partienbank (`bank/`, etwa 5 GB pro Monat) und fortsetzbare Downloads (`download/`) liegen. Spätere Analysen brauchen Sekunden pro Monat | `~/lichess-data` |
| `--keep-raw` | Die 29 GB Monatsdatei nach dem Bau der Banktabelle behalten. Sonst wird sie gelöscht, sobald die Tabelle geprüft ist, die Bank bleibt | aus |
| `--out ORDNER` | Wohin die fertigen Dateien kommen | `repertoires` neben dem Tool |
| `--repertoire PGN` | Dein eigenes Repertoire, seine Züge werden markiert | aus |
| `--quick` | Probelauf mit geringer Stockfish Tiefe | aus |
| `--notation de` | Deutsche Figurenbuchstaben (S, L, T, D) in Namen und Kommentaren | englisch |
| `--plain` | Ohne Animation | Animation an |

Die vollständige Liste steht in der [ausführlichen Anleitung](docs/ANLEITUNG.md).

## Gut zu wissen

- Dauer: Der Download ist der langsame Teil, denn Lichess drosselt jede einzelne Verbindung. Bei einer Messung waren es mit einer Verbindung 0,6 MB/s (etwa 7 Stunden pro Monat), mit 4 Verbindungen 6 MB/s (etwa 1,5 bis 2 Stunden). Dein Wert kann abweichen. Danach rechnet Stockfish 15 bis 60 Minuten. Mit `--quick` siehst du das Ergebnis in wenigen Minuten, sobald die Partien da sind.
- Verbindungen: Der Download nutzt standardmäßig 4 Verbindungen. `REPERTOIRE_VERBINDUNGEN=6 bash repertoire.sh ...` ändert die Zahl, `1` nutzt eine einzige. Nach Strg+C setzt der Download dort fort, wo er war.
- Nochmal starten: Mit denselben Angaben nutzt das Skript die schon geladenen Partien und rechnet nur, was fehlt. Ein Monat, der schon in der Bank ist, wird nie neu gebaut.
- Linux: Statt Homebrew `sudo apt install python3-venv zstd pv mawk stockfish`, der Rest ist gleich.

## Lizenz

GPL 3.0, siehe [LICENSE](LICENSE). Daten: [Lichess Open Database](https://database.lichess.org), Engine: [Stockfish](https://stockfishchess.org).
