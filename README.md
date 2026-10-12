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

On the first run the script sets up everything it needs. Colour is `white` or `black`, moves use English notation. For Black, include your own reply in the starting moves.

```bash
# Black against 1.d4 with 1...d5, opponents rated 1600 to 2000, quick trial run first
bash repertoire.sh black "1. d4 d5" --elo 1600-2000 --quick

# More games: the last three months instead of one
bash repertoire.sh white "1. e4" --months 3
```

## What you get

The results land in the folder `repertoires` next to the tool folder (change it with `--out`).

| File | Content |
| --- | --- |
| `NAME.pgn` | Your repertoire, one chapter per line, sorted by how often you will meet it. Main lines run at least to move 15, rare lines are bundled at the end. |
| `NAME_quickstart.pgn` | The 15 most likely lines up to move 14, perfect for practice. |
| `NAME_strukturen.json` | The typical pawn structures with all numbers. |

Every line ends with a Stockfish evaluation, a model game and blue arrows for the typical setup that scored best in practice. Every chapter ends with your opponents' most frequent mistakes and how to punish them. The PGN comments are in German. Games, engine cache and `konfiguration.json` stay in `repertoires/arbeit/NAME`, so the tool folder stays clean.

## The idea behind it

A repertoire from a book tells you what is best in theory. This tool tells you what you will actually face at your level and how to meet it.

- **Practice first, engine second.** The games decide what goes in and in which order. Stockfish checks and corrects, it does not choose the topics.
- **Positions, not move orders.** Different move orders reaching the same position are counted together.
- **Mistakes that actually happen.** For every position you see which errors your opponents really make, how often, and what punishes them.
- **Plans, not only moves.** Each line ends with a model game, the best scoring setup and the pawn structure you are heading for.
- **Collect once, analyse often.** The slow part is the raw data. It becomes a game bank once. Every further repertoire only searches the bank, and Stockfish results are cached.

## The game bank

A Lichess month is a PGN of about 29 GB (compressed) with every game in full. For a repertoire you only need a small part of each game. The game bank keeps exactly that, one line per game, compressed with zstd. It is built once per month and then replaces the original.

**What is stored per game:**

| Field | Meaning |
| --- | --- |
| Site | Link to the game on Lichess |
| White, Black | Player names |
| WhiteElo, BlackElo | Ratings of both players |
| Result, Termination | Result and how the game ended (normal, time forfeit, ...) |
| TimeControl, Date | Time control (e.g. 180+2) and date |
| Half moves, last move | Length of the game and its final move |
| First 40 half moves | The opening, 20 moves for each side, in standard notation |

**What is left out:** clock times, engine evaluations, rating changes, opening names, comments, and the moves between half move 40 and the last one. Bullet games, bot games and games without ratings or result are not in the bank at all.

**Why this is better than keeping the big PGN:**

| | Original monthly file | Game bank |
| --- | --- | --- |
| Size per month | about 29 GB | about 5 GB (estimate from a 2 GB sample) |
| Format | PGN, has to be parsed game by game | one line per game, searched by the opening moves |
| Search for your starting moves | about 8 minutes (estimate) | under a minute (estimate) |
| Other opening, colour or rating range | read everything again | search the same table again |
| Content | everything, including bullet, bots and engine data | only what a repertoire needs |

The bank covers every opening and every rating range, so one bank serves any number of repertoires. The price: the games are only known up to move 20 (no endgame studies), and bullet games are missing. If you need them, build a second bank from the original with `bash gamebank.sh NEWFOLDER 2026-09 --archive FOLDER --with-bullet`, so keep the monthly files until you are sure you do not.

## How to work with it

1. **Try it cheaply.** Run with `--quick` first. Wrong starting moves are caught before anything is downloaded.
2. **First full run builds the game bank.** Add `--months 3 --bank FOLDER --archive FOLDER --delete-archive` and leave out `--quick`. Each 29 GB monthly file is deleted as soon as its table is built.
3. **Read in the right order.** Quickstart file first, then the main file as a reference.
4. **Study in small steps.** Import the PGN into a Lichess study and learn from the top, the order is the order of importance.
5. **Tune and rerun.** Settings are in `konfiguration.json` in the working folder. A rerun reuses games and engine results.
6. **Compare with your own repertoire** using `--repertoire PGN`. Your moves get marked.
7. **Refresh now and then.** New months go into the same bank.

The numbers are statistics of online games in your rating range, without bullet and bots. Lines with few games are noisy, evaluations are taken at a fixed depth, and the model game is an example, not a proof.

## Options

| Option | Meaning | Default |
| --- | --- | --- |
| `--elo FROM-TO` | Rating range of both players | 1800-2499 |
| `--month YYYY-MM` / `--month A..B` | One month or a range | last full month |
| `--months N` | The last N full months | off |
| `--bank FOLDER` | Game bank: every month becomes a compact table once (about 5 GB per month), later analyses take seconds per month | off |
| `--archive FOLDER` | Keep the monthly files (about 29 GB each) instead of only streaming them | off |
| `--delete-archive` / `--keep-archive` | Delete monthly files once the bank has them, or never. Without either you are asked once at the start | ask |
| `--out FOLDER` | Where the finished files go | `repertoires` next to the tool |
| `--repertoire PGN` | Your own repertoire, its moves get marked | off |
| `--quick` | Trial run with low Stockfish depth | off |
| `--notation de` | German piece letters (S, L, T, D) in names and comments | English |
| `--plain` | No animation | animation on |

The full list with all fine tuning settings is in the [full guide](docs/GUIDE.md).

## Good to know

- **Time:** one Lichess month is streamed from the internet (about 29 GB, nothing of it is stored). That takes 30 minutes to a few hours, then Stockfish needs 15 to 60 minutes. With `--quick` you see a result within minutes once the games are in.
- **Running again:** with the same arguments the script reuses games and only computes what is missing. A month that is already in the bank is never built again.
- **While you wait:** a knight hops across a small board for every step, with percent and time left.
- **Linux:** instead of Homebrew use `sudo apt install python3-venv zstd pv mawk stockfish`, the rest is the same.

## License

GPL 3.0, see [LICENSE](LICENSE). Data: [Lichess open database](https://database.lichess.org), engine: [Stockfish](https://stockfishchess.org).
