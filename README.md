# Eröffnungsrepertoire aus Lichess Daten

Baut für Weiß oder Schwarz ein kommentiertes Repertoire als PGN: die häufigsten Antworten des Gegners, wie diese Partien ausgehen und wie Stockfish die Endstellungen bewertet.

## Voraussetzungen (macOS)

```bash
brew install zstd pv mawk stockfish
pip3 install chess
```

Quellen:
- Lichess Open Database: https://database.lichess.org
- Lichess Elite Database (2500+ gegen 2300+): https://database.nikonoel.fr
- Stockfish: https://github.com/official-stockfish/Stockfish
- python-chess: https://github.com/niklasf/python-chess
- zstd: https://github.com/facebook/zstd, pv: https://www.ivarch.com/programs/pv.shtml, mawk: https://invisible-island.net/mawk/

## 1. Partien filtern

Monatsdatei laden (etwa 29 GB) oder direkt streamen, dann nach Startzügen filtern. Die Startzüge werden in englischer Notation angegeben.

```bash
# lokale Datei
bash lichess_filter.sh -s "1. e4" -i lichess_db_standard_rated_2026-09.pgn.zst -o partien.pgn --tsv partien.tsv

# direkt von Lichess streamen, nichts Großes wird gespeichert
bash lichess_filter.sh -s "1. d4 d5 2. c4" -m 2026-09 -o partien.pgn --tsv partien.tsv
```

| Option | Bedeutung | Standard |
|---|---|---|
| `-s` | Startzüge, z. B. `"1. e4 c5 2. Nf3"` | Pflicht |
| `-i` / `-m` | Datei (`.pgn.zst` oder `.pgn`) oder Monat `JJJJ-MM` | eins davon |
| `-o` | Ausgabe PGN | Pflicht |
| `--tsv` | zusätzlich Tabelle für `repertoire.py` | aus |
| `--elo-min` / `--elo-max` | beide Spieler in diesem Bereich | 1800 / 2499 |
| `--elo-einer` | mindestens ein Spieler ab diesem Wert | aus |
| `--mit-bullet`, `--mit-bots` | Bullet oder Bot Partien behalten | ohne |
| `--halbzuege` | Halbzüge in der Tabelle | 30 |

Ein Monat dauert je nach Rechner und Startzügen etwa 5 bis 15 Minuten. Mehrere Monate: Befehl je Monat ausführen und die Tabellen mit `cat` zusammenfügen.

## 2. Konfiguration anlegen

Eine JSON Datei je Repertoire, Vorlagen: `beispiel_weiss.json`, `beispiel_schwarz.json`.

| Feld | Bedeutung |
|---|---|
| `titel` | Name des Repertoires |
| `farbe` | `"weiss"` oder `"schwarz"` |
| `start` | Startzüge wie beim Filter |
| `daten` | Tabelle aus Schritt 1 |
| `system` | Regel, woran eine Partie als eigenes System zählt, z. B. `[{"zug": "Nf3", "spaetestens_zug": 3, "nicht_vorher": []}]`. Leer = alle Partien |
| `ohne_systemfilter` | erste Antworten des Gegners, die ohne Systemregel gezählt werden (z. B. ein Gambit) |
| `erste_antworten` | Anzahl der ersten Antworten des Gegners (Standard 10) |
| `antworten` | Antworten des Gegners je Zug (Standard 3) |
| `fruehe_zuege_ab_5_prozent` | Zugnummern, in denen zusätzlich jede Antwort ab 5 % kommt (Standard 2 und 3) |
| `min_partien` | Linie verzweigt nur ab so vielen Partien (Standard 20) |
| `bis_zug` | maximale Tiefe (Standard 15) |
| `hv_tiefe` | Zug des Gegners, an dem die Hauptvariante in Kapitel geteilt wird (Standard 4) |
| `kapitel_max` | größere Kapitel werden geteilt (Standard 800 Züge) |
| `repertoire_pgn` | optional: bestehendes Repertoire, eigene Züge daraus werden als Repertoirezug markiert, Kommentare übernommen |
| `kommentare_entfernen` | reguläre Ausdrücke für Sätze, die aus diesen Kommentaren entfallen |
| `anhang_pgn` | optional: PGN Dateien, deren Partien als Themenkapitel angehängt werden |
| `statistik` | `true` schreibt Anteil und Partienzahl an jeden Zug |
| `stockfish`, `tiefe`, `prozesse` | Pfad zur Engine, Suchtiefe (Standard 18), parallele Prozesse |
| `eco`, `ausgabe` | ECO für die Kopfzeilen, Name der PGN |

## 3. Repertoire bauen

```bash
python3 repertoire.py meine_konfiguration.json
```

Laden und Zählen dauert einige Minuten, Stockfish je nach Zahl der Linienenden länger. Ergebnisse von Stockfish landen in `<ausgabe>_stockfish.json`, ein zweiter Lauf rechnet nur Neues.

## Aufbau der PGN

- 01 Intro mit Regeln und Symbolerklärung, dazu die Hauptvariante.
- Teil 1: Hauptvariante, ein Kapitel je Antwort des Gegners an der Teilungsstelle.
- Weitere Teile: Abweichungen des Gegners von spät nach früh, große Kapitel nach dem nächsten Zug geteilt.
- Anhang mit Themenkapiteln, am Ende eine Zusammenfassung bis Zug 5.
- Hauptvariante ist der meistgespielte Zug, der eigene Repertoirezug steht markiert daneben.
- Am Linienende: Bewertungszeichen von Stockfish, grüner Pfeil für den besten Zug, Musterpartie mit dem höchsten Elo Schnitt.
- Zugumstellungen verweisen auf das Kapitel, in dem die Stellung zuerst vorkommt.
