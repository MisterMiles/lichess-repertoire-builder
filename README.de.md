![lichess repertoire builder](docs/banner.svg)

# lichess repertoire builder

[English](README.md) | **Deutsch**

Du sagst, welche Eröffnung du spielst. Das Werkzeug holt sich dazu echte Lichess Partien aus deinem Elo Bereich und baut daraus ein Repertoire als PGN: was deine Gegner wirklich spielen, wie die Partien ausgehen, wo sie am häufigsten Fehler machen und wie Stockfish die Stellungen sieht. Die PGN öffnest du in einer Lichess Studie oder in ChessBase.

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
bash repertoire.sh weiss "1. e4"
```

Fertig. Beim ersten Mal richtet das Skript alles Nötige selbst ein.

## Beispiele

```bash
# Weiß mit 1.e4, gegen alles, was Schwarz spielt
bash repertoire.sh weiss "1. e4"

# Schwarz gegen 1.d4 mit 1...d5, Gegner zwischen 1600 und 2000, zuerst als schneller Probelauf
bash repertoire.sh schwarz "1. d4 d5" --elo 1600-2000 --schnell
```

Züge schreibst du in englischer Notation: N Springer, B Läufer, R Turm, Q Dame, K König. Bei Schwarz gehört deine eigene Antwort mit in die Startzüge.

## Was du bekommst

Einen Ordner mit dem Namen deines Repertoires, darin:
- **`….pgn`**: dein Repertoire, ein Kapitel je Linie, sortiert danach, wie oft du sie in der Praxis bekommst (der Anteil steht im Kapitelnamen). Die Hauptvariante jedes Kapitels läuft mindestens bis Zug 12, seltene Linien stehen gebündelt am Ende. Am Linienende stehen Stockfish Bewertung, eine Musterpartie und blaue Pfeile für den Aufbau, der in der Praxis am besten gepunktet hat, am Kapitelende die häufigsten Fehler deiner Gegner samt Widerlegung. Dazu kommen die typischen Bauernstrukturen.
- **`…_quickstart.pgn`**: die 15 wahrscheinlichsten Linien bis Zug 14, ideal zum Üben.

## Gut zu wissen

- **Dauer:** Die Partien eines Lichess Monats werden aus dem Internet gestreamt (etwa 29 GB, nichts davon wird gespeichert). Das dauert je nach Leitung 30 Minuten bis einige Stunden. Danach rechnet Stockfish 15 bis 60 Minuten. Mit `--schnell` siehst du das Ergebnis in wenigen Minuten, sobald die Partien da sind.
- **Nochmal starten:** Mit den gleichen Angaben nutzt das Skript die schon geladenen Partien und rechnet nur, was fehlt.
- **Linux:** Statt Homebrew `sudo apt install python3-venv zstd pv mawk stockfish`, der Rest ist gleich.
- **Mehr Einstellungen:** Elo, Monat, eigenes Repertoire und alle Feineinstellungen stehen in der [ausführlichen Anleitung](docs/ANLEITUNG.md).

## Lizenz

GPL 3.0, siehe [LICENSE](LICENSE). Daten: [Lichess Open Database](https://database.lichess.org), Engine: [Stockfish](https://stockfishchess.org).
