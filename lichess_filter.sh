#!/bin/bash
# Filtert eine Lichess Monatsdatei (database.lichess.org) nach Startzügen,
# Elo, Bedenkzeit und Bots. Optional entsteht zusätzlich eine kompakte Tabelle
# (TSV) für repertoire.py.
#
# Beispiele:
#   bash lichess_filter.sh -s "1. e4" -i lichess_db_standard_rated_2026-09.pgn.zst -o partien.pgn --tsv partien.tsv
#   bash lichess_filter.sh -s "1. d4 d5 2. c4" -m 2026-09 -o partien.pgn --tsv partien.tsv
#   bash lichess_filter.sh -s "1. e4" -i datei.pgn.zst --elo-einer 2500 --elo-min 2300 --elo-max 3500 -o stark.pgn
#
# Optionen:
#   -s, --start "ZÜGE"   Startzüge in englischer Notation, z. B. "1. e4 c5 2. Nf3"   (Pflicht)
#   -i, --input DATEI    .pgn.zst oder .pgn (lokal)
#   -m, --monat JJJJ-MM  stattdessen direkt von database.lichess.org streamen (nichts wird gespeichert)
#   -o, --output DATEI   Ausgabe PGN (Pflicht)
#   --tsv DATEI          zusätzlich kompakte Tabelle für repertoire.py schreiben
#   --elo-min N          beide Spieler mindestens N        (Standard 1800)
#   --elo-max N          beide Spieler höchstens N         (Standard 2499)
#   --elo-einer N        mindestens ein Spieler ab N       (Standard 0, aus)
#   --mit-bullet         Bullet und UltraBullet behalten   (Standard: ohne)
#   --mit-bots           Bot Partien behalten              (Standard: ohne)
#   --halbzuege N        Halbzüge in der Tabelle           (Standard 30)

set -o pipefail
START=""; INPUT=""; MONAT=""; OUT=""; TSV=""
ELO_MIN=1800; ELO_MAX=2499; ELO_EINER=0; BULLET=0; BOTS=0; PLIES=30
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

while [ $# -gt 0 ]; do
  case "$1" in
    -s|--start) START="$2"; shift 2;;
    -i|--input) INPUT="$2"; shift 2;;
    -m|--monat) MONAT="$2"; shift 2;;
    -o|--output) OUT="$2"; shift 2;;
    --tsv) TSV="$2"; shift 2;;
    --elo-min) ELO_MIN="$2"; shift 2;;
    --elo-max) ELO_MAX="$2"; shift 2;;
    --elo-einer) ELO_EINER="$2"; shift 2;;
    --mit-bullet) BULLET=1; shift;;
    --mit-bots) BOTS=1; shift;;
    --halbzuege) PLIES="$2"; shift 2;;
    -h|--help) sed -n '2,26p' "$0"; exit 0;;
    *) echo "Unbekannte Option: $1"; exit 1;;
  esac
done
[ -z "$START" ] && { echo "Bitte Startzüge angeben, z. B. -s \"1. e4\""; exit 1; }
# "1.e4" wie "1. e4" behandeln
START=$(printf '%s' "$START" | sed -E 's/([0-9]+)\.([^ .])/\1. \2/g')
[ -z "$OUT" ] && { echo "Bitte Ausgabedatei angeben: -o datei.pgn"; exit 1; }
[ -z "$INPUT" ] && [ -z "$MONAT" ] && { echo "Bitte -i DATEI oder -m JJJJ-MM angeben"; exit 1; }

AWK=awk
command -v gawk >/dev/null 2>&1 && AWK=gawk
command -v mawk >/dev/null 2>&1 && AWK=mawk

# Quelle als Datenstrom
quelle() {
  if [ -n "$MONAT" ]; then
    curl -fL --retry 5 --retry-delay 10 "https://database.lichess.org/standard/lichess_db_standard_rated_${MONAT}.pgn.zst" | zstd -dc
  elif [[ "$INPUT" == *.zst ]]; then
    if command -v pv >/dev/null 2>&1; then pv "$INPUT" | zstd -dc; else zstd -dc "$INPUT"; fi
  else
    if command -v pv >/dev/null 2>&1; then pv "$INPUT"; else cat "$INPUT"; fi
  fi
}

filter() {
LC_ALL=C "$AWK" -v start="$START" -v emin="$ELO_MIN" -v emax="$ELO_MAX" -v eeiner="$ELO_EINER" \
  -v bullet="$BULLET" -v bots="$BOTS" '
function norm(s) {
  gsub(/\{[^}]*\}/, "", s); gsub(/\([^()]*\)/, "", s)
  gsub(/[0-9]+\.\.\./, "", s); gsub(/[?!]+/, "", s); gsub(/[ \t]+/, " ", s)
  sub(/^ /, "", s); return s " "
}
BEGIN { st = norm(start); split(st, f, " "); first = f[1] " " f[2] " " }
function flush() {
  if (n == 0) return
  ok = (index(moves, first) == 1)
  if (ok && length(st) > length(first)) ok = (index(norm(moves), st) == 1)
  if (ok && !bullet && ev ~ /Bullet/) ok = 0
  if (ok && !bots && bot) ok = 0
  if (ok && (we == "" || be == "")) ok = 0
  if (ok) {
    hi = (we + 0 > be + 0) ? we + 0 : be + 0; lo = (we + 0 > be + 0) ? be + 0 : we + 0
    ok = (lo >= emin && hi <= emax && hi >= eeiner)
  }
  if (ok) { printf "%s", buf; print ""; kept++ }
  total++
  if (total % 2000000 == 0) printf "  %d Partien geprüft, %d behalten\n", total, kept > "/dev/stderr"
  buf = ""; moves = ""; ev = ""; we = ""; be = ""; n = 0; bot = 0
}
/^\[Event / { flush(); ev = $0 }
/^\[WhiteElo / { we = $2; gsub(/[^0-9]/, "", we) }
/^\[BlackElo / { be = $2; gsub(/[^0-9]/, "", be) }
/^\[(White|Black)Title "BOT"\]/ { bot = 1 }
{
  buf = buf $0 "\n"; n++
  if ($0 !~ /^\[/ && $0 != "") moves = moves (moves == "" ? "" : " ") $0
}
END { flush(); printf "Fertig: %d Partien geprüft, %d behalten\n", total, kept > "/dev/stderr" }
'
}

if [ -n "$MONAT" ] || [[ "$INPUT" == *.zst ]]; then
  command -v zstd >/dev/null 2>&1 || { echo "zstd fehlt: brew install zstd"; exit 1; }
fi

echo "Filter: Start \"$START\", Elo $ELO_MIN bis $ELO_MAX$( [ "$ELO_EINER" -gt 0 ] && echo ", einer ab $ELO_EINER"), Bullet $( [ $BULLET = 1 ] && echo mit || echo ohne), Bots $( [ $BOTS = 1 ] && echo mit || echo ohne)" >&2
if quelle | filter > "$OUT.tmp"; then
  mv "$OUT.tmp" "$OUT"
  echo "Gespeichert: $OUT" >&2
else
  echo "Fehler. Teildatei bleibt als $OUT.tmp liegen." >&2; exit 1
fi

if [ -n "$TSV" ]; then
  LC_ALL=C "$AWK" -v plies="$PLIES" -f "$DIR/pgn_tabelle.awk" "$OUT" > "$TSV"
  echo "Tabelle: $TSV ($(wc -l < "$TSV" | tr -d ' ') Partien)" >&2
fi
