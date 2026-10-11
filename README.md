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
bash repertoire.sh weiss "1. e4"
```

That's it. On the first run the script sets up everything it needs.

## Examples

```bash
# White with 1.e4, against everything Black plays
bash repertoire.sh weiss "1. e4"

# Black against 1.d4 with 1...d5, opponents rated 1600 to 2000, quick trial run first
bash repertoire.sh schwarz "1. d4 d5" --elo 1600-2000 --schnell
```

`weiss` means White, `schwarz` means Black (`white` and `black` work too). Moves use English notation. For Black, include your own reply in the starting moves.

## What you get

A folder named after your repertoire, containing:
- **`….pgn`**: your repertoire, split into chapters for the main line and the deviations. The chapter name shows how often you will meet the line in practice. Every line ends with a Stockfish evaluation and a model game, every chapter ends with your opponents' most frequent mistakes and how to punish them. Typical pawn structures are included too.
- **`…_quickstart.pgn`**: the 15 most likely lines up to move 14, perfect for practice.

The PGN comments are in German.

## Good to know

- **Time:** the games of one Lichess month are streamed from the internet (about 29 GB, nothing of it is stored). Depending on your connection this takes 30 minutes to a few hours. Stockfish then needs 15 to 60 minutes. With `--schnell` you see a result within minutes once the games are in.
- **Running again:** with the same arguments the script reuses the downloaded games and only computes what is missing.
- **Linux:** instead of Homebrew use `sudo apt install python3-venv zstd pv mawk stockfish`, the rest is the same.
- **More settings:** rating range, month, your own repertoire and every fine tuning option are in the [full guide](docs/GUIDE.md).

## License

GPL 3.0, see [LICENSE](LICENSE). Data: [Lichess open database](https://database.lichess.org), engine: [Stockfish](https://stockfishchess.org).
