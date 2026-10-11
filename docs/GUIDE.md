# Full guide

[Short version](../README.md) | [Deutsch](ANLEITUNG.md)

This guide covers every option. For a quick start, the [README](../README.md) is enough.

Builds an annotated opening repertoire as PGN, for White or Black: the opponent's most frequent replies, how those games end, how Stockfish evaluates the positions, where the opponent most often goes wrong and which pawn structures are typical. A small quickstart PGN with the most likely lines is created as well, for fast practice.

The scripts, their console output and the generated PGN comments are in German. The configuration keys are German too, every key is explained below.

## Requirements

Always needed:
- **Python 3** with the package `chess` (python-chess). Tested with 3.13, 3.9 or newer should work.
- **Stockfish**. Set its name or full path in the configuration under `"stockfish"`.
- **For the filter script:** `bash`, `awk` (`mawk` is much faster, the script picks the fastest one available), `zstd`, `curl` for `-m`, optionally `pv` for a progress display.
- **Disk:** a monthly file is about 29 GB. With `-m` the file is streamed and not stored. `repertoire.sh` streams as well, unless you use `--archive`.
- **Memory:** all filtered games are loaded at once. Not measured yet, very large data sets may need a lot of RAM.

### macOS

```bash
brew install zstd pv mawk stockfish
python3 -m venv ~/.venv-repertoire
~/.venv-repertoire/bin/pip install chess
```

Homebrew's Python blocks `pip install` into the system as well, hence the virtual environment. Run the script with `~/.venv-repertoire/bin/python repertoire.py ...`.

### Linux (Debian, Ubuntu)

```bash
sudo apt install zstd pv mawk stockfish python3-venv
python3 -m venv ~/.venv-repertoire
~/.venv-repertoire/bin/pip install chess
```

Recent distributions block `pip install` into the system Python, hence the virtual environment. Run the script with `~/.venv-repertoire/bin/python repertoire.py ...`. The distribution's Stockfish package is often older, current builds are available at https://stockfishchess.org/download/.

### What has been tested

| | Filter script | repertoire.py |
|---|---|---|
| Linux | tested | tested (Python 3.13) |
| macOS | tested | tested |

Sources:
- Lichess open database: https://database.lichess.org
- Lichess Elite Database (2500+ vs 2300+): https://database.nikonoel.fr
- Stockfish: https://github.com/official-stockfish/Stockfish
- python-chess: https://github.com/niklasf/python-chess
- zstd: https://github.com/facebook/zstd, pv: https://www.ivarch.com/programs/pv.shtml, mawk: https://invisible-island.net/mawk/

## The one command way: repertoire.sh

`repertoire.sh` runs all steps below in one go: it sets up a Python environment, streams and filters the games, writes `konfiguration.json` and builds the repertoire. Everything lands in one folder.

```bash
bash repertoire.sh white "1. e4"
bash repertoire.sh black "1. d4 d5" --elo 1600-2000 --quick
```

| Option | Meaning | Default |
|---|---|---|
| `--elo FROM-TO` | rating range of both players | 1800-2499 |
| `--month YYYY-MM` (`--monat`) | Lichess month, several as `YYYY-MM..YYYY-MM` | last full month |
| `--months N` (`--monate`) | the last N full months | off |
| `--bank FOLDER` | game bank: every month is turned once into a table of all games (no bullet, no bots, about 5 GB per month). Further analyses only search in it, a few seconds per month. With `--archive` the bank is built from the stored monthly files, otherwise streamed | off |
| `--archive FOLDER` (`--archiv`) | keep the monthly files there instead of only streaming (about 29 GB each), existing ones are reused | off |
| `--file FILE` (`--datei`) | your own Lichess file (`.pgn` or `.pgn.zst`) instead of the download | off |
| `--name NAME` | folder name for the results | from colour and moves |
| `--repertoire PGN` | your own repertoire, its moves get marked | none |
| `--plain` | no knight animation, plain output (automatic when the output goes to a file) | off |
| `--quick` (`--schnell`) | quick trial run with low Stockfish depth | off |
| `--notation de` | German piece letters (S, L, T, D) in chapter names and comments | English (N, B, R, Q) |

Running it again with the same arguments reuses the games and the Stockfish results. For fine tuning, edit `konfiguration.json` in the folder (keys below) and run again.

The sections below describe the single steps for full control.

## Game bank for many analyses

`gamebank.sh` turns Lichess months once into compact tables of all games, without bullet and bots, with every opening and rating range and the first 40 half moves. `repertoire.sh --bank FOLDER` calls it automatically and afterwards only searches the bank.

```bash
bash gamebank.sh ~/gamebank 2026-07 2026-08 2026-09
bash gamebank.sh ~/gamebank 2026-09 --archive ~/lichess    # from stored monthly files
```

| Option | Meaning | Default |
|---|---|---|
| `--archive FOLDER` (`--archiv`) | read monthly files from there, download missing ones into it | stream |
| `--with-bullet` (`--mit-bullet`) | include bullet games | without |
| `--jobs N` (`--teile`) | parallel processes | CPU cores minus one, at most 8 |

Measured on a 2 GB slice of September 2026: 63 % of the games remain (no bullet, no bots), the bank is about 2.4 % of the unpacked PGN. Extrapolated that is roughly 5 GB per month instead of 29 GB, and searching for starting moves then takes under a minute per month instead of about 8 minutes.

## 1. Filter games

Download a monthly file (about 29 GB) or stream it directly, then filter by your starting moves. Moves use English notation.

```bash
# local file
bash lichess_filter.sh -s "1. e4" -i lichess_db_standard_rated_2026-09.pgn.zst -o games.pgn --tsv games.tsv

# stream straight from Lichess, nothing large is stored
bash lichess_filter.sh -s "1. d4 d5 2. c4" -m 2026-09 -o games.pgn --tsv games.tsv
```

| Option | Meaning | Default |
|---|---|---|
| `-s` | starting moves, e.g. `"1. e4 c5 2. Nf3"` | required unless `--contains` is used |
| `-i` / `-m` | file (`.pgn.zst` or `.pgn`) or month `YYYY-MM` | one of them |
| `-o` | output PGN | required |
| `--tsv` | also write the table for `repertoire.py` | off |
| `--elo-min` / `--elo-max` | both players within this range | 1800 / 2499 |
| `--elo-one` (`--elo-einer`) | at least one player at or above this rating | off |
| `--with-bullet`, `--with-bots` (`--mit-bullet`, `--mit-bots`) | keep bullet or bot games | excluded |
| `--plies` (`--halbzuege`) | half moves stored in the table | 40 |
| `--contains` (`--enthaelt`) | a move that appears anywhere in the first moves (for transpositions) | off |
| `--move-color` (`--zug-farbe`) | who plays that move, `white` or `black` | white |
| `--by-move` (`--bis-zug`) | at the latest in this move | 5 |
| `--not-start` (`--nicht-start`) | exclude games that start with these moves | off |

For Black, include White's first move and your own reply in the starting moves, e.g. `"1. d4 d5"`. Otherwise the script takes the most played reply as the main line, which may not be yours.

One month takes about 5 to 15 minutes depending on the machine and the starting moves. For several months, run the command per month and join the tables with `cat`. `repertoire.sh` does this automatically with `--months` or `--month FROM..TO` and remembers every finished month in the subfolder `monate`.

## 2. Create a configuration

One JSON file per repertoire, templates: `beispiel_weiss.json` (White), `beispiel_schwarz.json` (Black). Only set the keys that differ from the default.

| Key | Meaning | Default |
|---|---|---|
| `titel`, `farbe`, `start`, `daten`, `ausgabe` | name, `"weiss"` or `"schwarz"`, starting moves, table from step 1, output PGN | required |
| `system` | what makes a game count as your own system, e.g. `[{"zug": "Nf3", "spaetestens_zug": 3, "nicht_vorher": []}]` (move, at the latest in move, not after these moves) | all games |
| `ohne_systemfilter` | first opponent replies counted without the system rule (e.g. a gambit) | none |
| `erste_antworten` | number of first opponent replies | 10 |
| `antworten` | opponent replies per move | 3 |
| `fruehe_zuege_ab_5_prozent` | move numbers where every reply of 5 % or more is added | 2 and 3 |
| `min_partien` | a line branches only with at least this many games | 20 |
| `bis_zug` | maximum depth (move number) | 15 |
| `hv_tiefe` | opponent move at which the main line is split into chapters | 4 |
| `kapitel_max` | larger chapters are split | 800 moves |
| `kapitel_min_anteil` | chapters reached by fewer games (in % of all) are merged per branch point and placed at the end | 2 |
| `kapitel_min_zug`, `verlaengern_min_partien` | every chapter's main line runs at least to this move: most played moves while at least this many games remain, then Stockfish | 15, 5 |
| `repertoire_pgn` | existing repertoire, your moves in it are marked as repertoire moves, comments are kept | none |
| `repertoire_zuege` | `"alle"`: every own move in that file is a repertoire move, `"hauptzug"`: only the first one per position | alle |
| `kommentare_entfernen` | regular expressions for sentences to drop from those comments | none |
| `anhang_pgn` | PGN files whose games are appended as theme chapters | none |
| `statistik` | write share and number of games at every move | off |
| `quickstart_linien`, `quickstart_bis_zug` | number and length of the quickstart lines | 15, move 14 |
| `fehler` | look for frequent opponent mistakes per chapter | on |
| `fehler_grenze` | loss on the winning chances scale from which a move counts as a mistake (0.2 is the Lichess threshold for "mistake", about one pawn in a balanced position) | 0.2 |
| `fehler_min_partien`, `fehler_min_anteil`, `fehler_anzahl` | a move is checked only with at least this many games and this share, the most frequent ones are shown | 10, 5 %, 5 |
| `plan_zuege`, `plan_min_partien` | own moves shown as the typical setup from practice at each line end, and the minimum number of games for it | 5, 5 |
| `strukturen_zug`, `strukturen_anzahl` | move and number of pawn structures | move 12, 5 |
| `strukturen_text` | JSON file with your own explanation per structure (`{"id": "text"}`, the ids are listed in `<output>_strukturen.json`) | none |
| `stockfish`, `tiefe`, `fehler_tiefe`, `prozesse` | engine path, search depth at line ends and for the mistake search, parallel processes | stockfish, 18, 14, 2 |
| `eco` | ECO code for the headers | ? |
| `notation` | piece letters in chapter names and comments: `en` (N, B, R, Q) or `de` (S, L, T, D). The moves in the PGN are always standard | en |

## 3. Build the repertoire

```bash
python3 repertoire.py my_configuration.json
```

Outputs:
- `<output>.pgn`: the repertoire
- `<output>_quickstart.pgn`: the most likely lines up to move 14, one chapter per line. Where the data ends, the line continues with Stockfish's best move, marked with a comment.
- `<output>_strukturen.json`: the pawn structures with all numbers, a base for your own explanations
- `<output>_stockfish.json`: engine cache

### Runtime and progress

The script runs in six steps and shows a progress bar with percentage, count and estimated time left for the long steps:

```
1/6 Daten
  Partien laden [██████████░░░░░░░░░░]  52,0 %  97456/187412  noch ca. 4 Min.
3/6 Stockfish
  Stockfish     [████░░░░░░░░░░░░░░░░]  21,3 %  560/2613  noch ca. 38 Min.
```

Rough values for about 190,000 games with 2 processes: loading 10 minutes, Stockfish 30 to 90 minutes (the biggest part, depends on `tiefe`, `fehler_tiefe` and the number of lines), model games 5 minutes, writing under a minute. More `prozesse` speed up Stockfish almost linearly, the number of CPU cores minus one is a good choice. Stopping is safe: Stockfish results are saved continuously and a new run only computes what is missing.

## Structure of the repertoire PGN

- 01 Intro with rules and symbols, plus the main line.
- Chapters are sorted by how often you will meet them, the most likely first. Chapters below 2 % are merged per branch point into "Seltene Abweichungen" at the end.
- Every chapter's main line runs at least to move 15: most played moves while at least 5 games remain, then Stockfish's best moves (marked in a comment). If the main line ends in a transposition, it continues with the main line from there.
- The chapter name shows the share of all evaluated games that reach the chapter, e.g. `(4,2 % gesamt)`.
- The main line is the most played move, your repertoire move is marked next to it.
- Line ends: Stockfish evaluation symbol, model game with the highest average rating and blue arrows for the typical setup from practice: your next 3 own moves (captures left out) that scored best after this position, at least 5 games. With fewer games a green arrow shows Stockfish's best move instead.
- End of each chapter: the opponent's most frequent mistakes. A move counts as a mistake if it loses at least `fehler_grenze` winning chances according to Stockfish. Each mistake shows the evaluation before and after and your score after this move compared with the other moves in the same position. In the tree the move is marked ? or ??, together with the refutation.
- Pawn structures: the most frequent central structures (files c to f) after move 12, one chapter each with an example position. Known structures are named (e.g. Stonewall, Carlsbad, isolated queen's pawn, French, King's Indian) and come with the standard plans. Features of the example position are described automatically (isolated, doubled and passed pawns, open and half open files, knight outposts). On the board, yellow squares mark the typical squares of your minor pieces, arrows show the most frequent pawn breaks (green yours, red the opponent's), and the breaks of the side to move can be clicked through as variations.
- Appendix with theme chapters, a summary up to move 5 at the end.
- Transpositions refer to the chapter where the position first appears.

## Measure transpositions from other move orders

The repertoire only counts games that start with the starting moves. `zugumstellungen.py` measures how many games reach the same positions through other move orders:

```bash
# games in which your key move comes later
bash lichess_filter.sh --contains d4 --by-move 4 --not-start "1. d4" -i month.pgn.zst -o other.pgn --tsv other.tsv
python3 zugumstellungen.py my_configuration.json other.tsv
```

The result shows how many additional games reach a position of the repertoire and through which move orders.

## License

GPL 3.0, in line with python-chess and Stockfish. See [LICENSE](../LICENSE).
