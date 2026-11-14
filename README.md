![lichess repertoire builder](docs/banner.svg)

# lichess repertoire builder

**English** | [Deutsch](README.de.md)

Tell it which opening you play. The tool takes real Lichess games from your rating range and builds a repertoire PGN: what your opponents actually play, where they go wrong most often and how Stockfish sees the positions. Open the PGN in a Lichess study or in ChessBase.

[Quick start](#quick-start-mac) · [The idea](#the-idea-behind-it) · [Game bank](#the-game-bank) · [How to work with it](#how-to-work-with-it) · [Options](#options) · [Good to know](#good-to-know)

## Quick start (Mac)

**1. Install the programs** (once, in the Terminal app). If Homebrew is missing, run the line from [brew.sh](https://brew.sh) first.

```bash
brew install python zstd pv mawk stockfish
```

**2. Download the tool**

```bash
git clone https://github.com/MisterMiles/lichess-repertoire-builder.git
cd lichess-repertoire-builder
```

Without git: click "Code" and then "Download ZIP" on GitHub, unzip it and `cd` into the folder.

**3. Build your repertoire**

```bash
bash repertoire.sh white "1. e4"
```

```bash
# Black against 1.d4 with 1...d5, opponents rated 1600 to 2000, quick trial run first
bash repertoire.sh black "1. d4 d5" --elo 1600-2000 --quick
```

For the first full run, use `--archive`. The download is about 29 GB per month and takes hours, so it may well get interrupted. With `--archive` it uses several connections and continues where it stopped when you rerun the command. Without it, an interrupted month starts from zero. Add `--bank` so later repertoires skip the download:

```bash
bash repertoire.sh white "1. e4" --months 3 --bank ~/gamebank --archive ~/lichess --delete-archive
```

## What you get

The results go to `repertoires` next to the tool folder (`--out` changes it).

| File | Content |
| --- | --- |
| `NAME.pgn` | Your repertoire, one chapter per line, sorted by how often you will meet it. Main lines run at least to move 15, rare lines are bundled at the end. |
| `NAME_quickstart.pgn` | The 15 most likely lines up to move 14, for practice. |
| `NAME_strukturen.json` | The typical pawn structures with all numbers. |

Every line ends with a Stockfish evaluation, a model game and blue arrows for the setup that scored best in practice. Every chapter ends with your opponents' most frequent mistakes and how to punish them. The PGN comments are in German. Games, engine cache and `konfiguration.json` stay in `repertoires/arbeit/NAME`.

## The idea behind it

A book repertoire tells you what is best in theory. This tool tells you what you will actually face at your level. The games decide what goes in and in which order, and Stockfish only checks and corrects. Different move orders that reach the same position are counted together. For every position you see which mistakes your opponents really make and what punishes them. The slow part is the raw data: it becomes a game bank once, and every further repertoire only searches the bank.

## The game bank

A Lichess month is a PGN of about 29 GB compressed. A repertoire needs only a small part of each game, so the bank keeps one zstd-compressed line per game: the link to the game, player names, both ratings, result and termination, time control and date, game length, last move and the first 40 half moves. It leaves out clock times, engine evaluations, rating changes, opening names, comments and the moves between half move 40 and the last one. Bullet games, bot games and games without ratings or result are not in it.

A month shrinks to about 5 GB (estimate from a 2 GB sample), and a search for your starting moves takes under a minute instead of about 8 (estimate). One bank covers every opening, colour and rating range, so it serves any number of repertoires.

The price: games are known only up to move 20, so there are no endgame studies, and bullet is missing. For bullet, build a second bank from the original with `bash gamebank.sh NEWFOLDER 2026-09 --archive FOLDER --with-bullet`. Keep the monthly files until you are sure you do not need it.

## How to work with it

1. Run with `--quick` first. Wrong starting moves show up before anything is downloaded.
2. The first full run builds the game bank: add `--months 3 --bank FOLDER --archive FOLDER --delete-archive` and leave out `--quick`. Each monthly file is deleted once its table is built.
3. Read the quickstart file first, then the main file as a reference. Import the PGN into a Lichess study and learn from the top, since the order is the order of importance.
4. Settings are in `konfiguration.json` in the working folder, and a rerun reuses games and engine results. `--repertoire PGN` marks your own moves.
5. New months go into the same bank.

The numbers are statistics of online games in your rating range, without bullet and bots. Lines with few games are noisy, evaluations use a fixed depth, and the model game is an example, not a proof.

## Options

| Option | Meaning | Default |
| --- | --- | --- |
| `--elo FROM-TO` | Rating range of both players | 1800-2499 |
| `--month YYYY-MM` / `--month A..B` | One month or a range | last full month |
| `--months N` | The last N full months | off |
| `--bank FOLDER` | Game bank: every month becomes a compact table once (about 5 GB), later analyses take seconds per month | off |
| `--archive FOLDER` | Keep the monthly files (about 29 GB each) instead of only streaming them | off |
| `--delete-archive` / `--keep-archive` | Delete monthly files once the bank has them, or never. Without either you are asked once at the start | ask |
| `--out FOLDER` | Where the finished files go | `repertoires` next to the tool |
| `--repertoire PGN` | Your own repertoire, its moves get marked | off |
| `--quick` | Trial run with low Stockfish depth | off |
| `--notation de` | German piece letters (S, L, T, D) in names and comments | English |
| `--plain` | No animation | animation on |

The full list is in the [full guide](docs/GUIDE.md).

## Good to know

- Time: the download is the slow part, because Lichess throttles each connection. In one measurement a single connection gave 0.6 MB/s (about 7 hours per month) and `--archive` with 4 connections gave 6 MB/s (about 1.5 to 2 hours). Yours may differ. Stockfish then needs 15 to 60 minutes. With `--quick` you see a result within minutes once the games are in.
- Connections: several connections work only with `--archive` (default 4). Without it the file is streamed over one connection and is much slower. `REPERTOIRE_VERBINDUNGEN=6 bash repertoire.sh ...` changes the number, `1` uses a single connection. After Ctrl+C the download continues where it stopped.
- Running again: with the same arguments the script reuses games and computes only what is missing. A month already in the bank is never built again.
- Linux: instead of Homebrew use `sudo apt install python3-venv zstd pv mawk stockfish`, the rest is the same.

## License

GPL 3.0, see [LICENSE](LICENSE). Data: [Lichess open database](https://database.lichess.org), engine: [Stockfish](https://stockfishchess.org).
