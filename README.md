![lichess repertoire builder](docs/banner.svg)

# lichess repertoire builder

**English** | [Deutsch](README.de.md)

Tell it which opening you play. The tool grabs real Lichess games from your rating range and turns them into a repertoire PGN: what your opponents actually play, how those games end, where they go wrong most often and how Stockfish sees the positions. Open the PGN in a Lichess study or in ChessBase.

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

Without git: click "Code" and then "Download ZIP" on GitHub, unzip it and `cd` into the folder in the Terminal.

**3. Build your repertoire**

```bash
bash repertoire.sh white "1. e4"
```

That's it. On the first run the script sets up everything it needs.

## Examples

```bash
# White with 1.e4, against everything Black plays
bash repertoire.sh white "1. e4"

# Black against 1.d4 with 1...d5, opponents rated 1600 to 2000, quick trial run first
bash repertoire.sh black "1. d4 d5" --elo 1600-2000 --quick

# More games: the last three months instead of one
bash repertoire.sh white "1. e4" --months 3
```

Colour is `white` or `black`. Moves use English notation. For Black, include your own reply in the starting moves.

## What you get

The results land in the folder `repertoires` next to the tool folder (change it with `--out FOLDER`):
- **`….pgn`**: your repertoire, one chapter per line, sorted by how often you will meet it in practice (the share is in the chapter name). Every chapter's main line runs at least to move 15, rare lines are bundled at the end. Every line ends with a Stockfish evaluation, a model game and blue arrows for the typical setup that scored best in practice, every chapter ends with your opponents' most frequent mistakes and how to punish them. Typical pawn structures are included too.
- **`…_quickstart.pgn`**: the 15 most likely lines up to move 14, perfect for practice.

Games, Stockfish cache and `konfiguration.json` stay in `repertoires/arbeit/NAME`, so the tool folder stays clean.

The PGN comments are in German.

## Good to know

- **Time:** the games of one Lichess month are streamed from the internet (about 29 GB, nothing of it is stored). Depending on your connection this takes 30 minutes to a few hours. Stockfish then needs 15 to 60 minutes. With `--quick` you see a result within minutes once the games are in.
- **More games:** `--months 3` takes the last three full months, `--month 2026-07..2026-09` a fixed range. Every month is downloaded and filtered on its own, so the waiting time grows with it. With `--archive FOLDER` the monthly files are kept (about 29 GB each) and are not downloaded again next time.
- **Several analyses:** with `--bank FOLDER` every month is turned once into a game bank, a compact table of all games (about 5 GB per month). After that every further analysis with other starting moves, colour or rating range needs only seconds per month before Stockfish starts. Example: `bash repertoire.sh white "1. e4" --months 3 --bank ~/gamebank`. A month that is in the bank is never built again, and with `--archive` plus `--delete-archive` the 29 GB monthly file is deleted as soon as its bank table is built.
- **While you wait:** a knight hops across a small board for every step, with percent and time left. `--plain` switches it off.
- **Running again:** with the same arguments the script reuses the downloaded games and only computes what is missing.
- **Linux:** instead of Homebrew use `sudo apt install python3-venv zstd pv mawk stockfish`, the rest is the same.
- **More settings:** rating range, month, your own repertoire and every fine tuning option are in the [full guide](docs/GUIDE.md).

## License

GPL 3.0, see [LICENSE](LICENSE). Data: [Lichess open database](https://database.lichess.org), engine: [Stockfish](https://stockfishchess.org).
