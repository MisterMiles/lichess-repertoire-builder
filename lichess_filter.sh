#!/bin/bash
# Filters a Lichess monthly file (database.lichess.org) by starting moves, rating,
# time control and bots. Optionally also writes a compact table (TSV) for repertoire.py.
#
# Examples:
#   bash lichess_filter.sh -s "1. e4" -i lichess_db_standard_rated_2026-09.pgn.zst -o games.pgn --tsv games.tsv
#   bash lichess_filter.sh -s "1. d4 d5 2. c4" -m 2026-09 -o games.pgn --tsv games.tsv
#   bash lichess_filter.sh -s "1. e4" -i file.pgn.zst --elo-one 2500 --elo-min 2300 --elo-max 3500 -o strong.pgn
#
# Options (German names in brackets work as well):
#   -s, --start "MOVES"     starting moves in English notation, e.g. "1. e4 c5 2. Nf3"
#   --contains MOVE         instead: this move appears in the first moves (--enthaelt, for transpositions)
#   --move-color white|black  who plays the move from --contains (--zug-farbe, default white)
#   --by-move N             at the latest in move N (--bis-zug, default 5)
#   --not-start "MOVES"     exclude games starting like this (--nicht-start)
#   -i, --input FILE        .pgn.zst or .pgn (local)
#   -m, --month YYYY-MM     instead stream from database.lichess.org, nothing is stored (--monat)
#   -o, --output FILE       output PGN (required)
#   --tsv FILE              also write a compact table for repertoire.py
#   --elo-min N             both players at least N              (default 1800)
#   --elo-max N             both players at most N               (default 2499)
#   --elo-one N             at least one player from N (--elo-einer, default 0, off)
#   --with-bullet           keep bullet and ultrabullet (--mit-bullet, default: without)
#   --with-bots             keep bot games (--mit-bots, default: without)
#   --plies N               half moves in the table (--halbzuege, default 40)
#   --plain                 no animation, plain output (also: REPERTOIRE_PLAIN=1)

set -o pipefail
START=""; ENTH=""; ZFARBE="weiss"; BISZUG=5; NSTART=""; INPUT=""; MONAT=""; OUT=""; TSV=""
ELO_MIN=1800; ELO_MAX=2499; ELO_EINER=0; BULLET=0; BOTS=0; PLIES=40
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/animation.sh"

while [ $# -gt 0 ]; do
  case "$1" in
    -s|--start) START="$2"; shift 2;;
    -i|--input) INPUT="$2"; shift 2;;
    --contains|--enthaelt) ENTH="$2"; shift 2;;
    --move-color|--zug-farbe) ZFARBE="$2"; shift 2;;
    --by-move|--bis-zug) BISZUG="$2"; shift 2;;
    --not-start|--nicht-start) NSTART="$2"; shift 2;;
    -m|--month|--monat) MONAT="$2"; shift 2;;
    -o|--output) OUT="$2"; shift 2;;
    --tsv) TSV="$2"; shift 2;;
    --elo-min) ELO_MIN="$2"; shift 2;;
    --elo-max) ELO_MAX="$2"; shift 2;;
    --elo-one|--elo-einer) ELO_EINER="$2"; shift 2;;
    --with-bullet|--mit-bullet) BULLET=1; shift;;
    --with-bots|--mit-bots) BOTS=1; shift;;
    --plies|--halbzuege) PLIES="$2"; shift 2;;
    --plain) export REPERTOIRE_PLAIN=1; shift;;
    -h|--help|--hilfe) sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "Unknown option: $1"; exit 1;;
  esac
done
[ -z "$START" ] && [ -z "$ENTH" ] && { echo "Bitte Startzüge (-s \"1. e4\") oder --enthaelt ZUG angeben"; exit 1; }
# "1.e4" wie "1. e4" behandeln
START=$(printf '%s' "$START" | sed -E 's/([0-9]+)\.([^ .])/\1. \2/g')
NSTART=$(printf '%s' "$NSTART" | sed -E 's/([0-9]+)\.([^ .])/\1. \2/g')
[ -z "$OUT" ] && { echo "Bitte Ausgabedatei angeben: -o datei.pgn"; exit 1; }
[ -z "$INPUT" ] && [ -z "$MONAT" ] && { echo "Bitte -i DATEI oder -m JJJJ-MM angeben"; exit 1; }

AWK=awk
command -v gawk >/dev/null 2>&1 && AWK=gawk
command -v mawk >/dev/null 2>&1 && AWK=mawk

URL="https://database.lichess.org/standard/lichess_db_standard_rated_${MONAT}.pgn.zst"
TITEL="${REPERTOIRE_TITEL:-Filtern $MONAT}"
ANIM=""; anim_an && ANIM=1
PVDATEI="$OUT.fortschritt"; INFODATEI="$OUT.info"

# Quelle als Datenstrom
quelle() {
  if [ -n "$ANIM" ]; then
    if [ -n "$MONAT" ]; then strom_url "$URL" "$PVDATEI" | zstd -dc
    elif [[ "$INPUT" == *.zst ]]; then strom_datei "$INPUT" "$PVDATEI" | zstd -dc
    else strom_datei "$INPUT" "$PVDATEI"; fi
  elif [ -n "$MONAT" ]; then
    curl -fL --retry 5 --retry-delay 10 "$URL" | zstd -dc
  elif [[ "$INPUT" == *.zst ]]; then
    if command -v pv >/dev/null 2>&1; then pv "$INPUT" | zstd -dc; else zstd -dc "$INPUT"; fi
  else
    if command -v pv >/dev/null 2>&1; then pv "$INPUT"; else cat "$INPUT"; fi
  fi
}

filter() {
LC_ALL=C "$AWK" -v start="$START" -v emin="$ELO_MIN" -v emax="$ELO_MAX" -v eeiner="$ELO_EINER" \
  -v bullet="$BULLET" -v bots="$BOTS" -v enth="$ENTH" -v zfarbe="$ZFARBE" -v biszug="$BISZUG" -v nstart="$NSTART" \
  -v info="$( [ -n "$ANIM" ] && echo "$INFODATEI" || echo /dev/stderr )" -v leise="$ANIM" '
function norm(s) {
  gsub(/\{[^}]*\}/, "", s); gsub(/\([^()]*\)/, "", s)
  gsub(/[0-9]+\.\.\./, "", s); gsub(/[?!]+/, "", s); gsub(/[ \t]+/, " ", s)
  sub(/^ /, "", s); return s " "
}
BEGIN { if (start != "") { st = norm(start); split(st, f, " "); first = f[1] " " f[2] " " }
        if (nstart != "") ns = norm(nstart); weiss = (zfarbe !~ /^[sbSB]/) }
function enthaelt(m,   s, t, n, i, nr, seite) {
  if (index(substr(m, 1, biszug * 70 + 200), enth) == 0) return 0
  s = norm(m); n = split(s, t, " "); nr = 0; seite = 0
  for (i = 1; i <= n; i++) {
    if (t[i] ~ /^[0-9]+\.$/) { nr = t[i] + 0; seite = 0; continue }
    if (nr > biszug) return 0
    if (t[i] == enth && ((seite == 0) == weiss)) return 1
    seite = 1
  }
  return 0
}
function flush() {
  if (n == 0) return
  if (start != "") {
    ok = (index(moves, first) == 1)
    if (ok && length(st) > length(first)) ok = (index(norm(moves), st) == 1)
  } else ok = 1
  if (ok && enth != "") ok = enthaelt(moves)
  if (ok && ns != "") ok = (index(norm(moves), ns) != 1)
  if (ok && !bullet && ev ~ /Bullet/) ok = 0
  if (ok && !bots && bot) ok = 0
  if (ok && (we == "" || be == "")) ok = 0
  if (ok) {
    hi = (we + 0 > be + 0) ? we + 0 : be + 0; lo = (we + 0 > be + 0) ? be + 0 : we + 0
    ok = (lo >= emin && hi <= emax && hi >= eeiner)
  }
  if (ok) { printf "%s", buf; print ""; kept++ }
  total++
  if (!leise && total % 2000000 == 0) printf "  %d Partien geprüft, %d behalten\n", total, kept > "/dev/stderr"
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
END { flush(); printf "Fertig: %d Partien geprüft, %d behalten\n", total, kept > info }
'
}

if [ -n "$MONAT" ] || [[ "$INPUT" == *.zst ]]; then
  command -v zstd >/dev/null 2>&1 || { echo "zstd fehlt: brew install zstd"; exit 1; }
fi

echo "Filter: Start \"$START\"$( [ -n "$ENTH" ] && echo ", enthält $ENTH bis Zug $BISZUG")$( [ -n "$NSTART" ] && echo ", ohne Anfang $NSTART"), Elo $ELO_MIN bis $ELO_MAX$( [ "$ELO_EINER" -gt 0 ] && echo ", einer ab $ELO_EINER"), Bullet $( [ $BULLET = 1 ] && echo mit || echo ohne), Bots $( [ $BOTS = 1 ] && echo mit || echo ohne)" >&2
[ -n "$ANIM" ] && { : > "$PVDATEI"; anim_start "$TITEL" --pv "$PVDATEI"; }
if quelle | filter > "$OUT.tmp"; then
  anim_stopp; [ -n "$ANIM" ] && { cat "$INFODATEI" >&2; rm -f "$INFODATEI" "$PVDATEI"; }
  mv "$OUT.tmp" "$OUT"
  echo "Gespeichert: $OUT" >&2
else
  anim_stopp; rm -f "$INFODATEI" "$PVDATEI"
  echo "Fehler. Teildatei bleibt als $OUT.tmp liegen." >&2; exit 1
fi

if [ -n "$TSV" ]; then
  # gleiche Tabelle wie in der Partienbank; gefiltert ist schon, deshalb Bullet und Bots hier nicht nochmal aussortieren
  LC_ALL=C "$AWK" -v plies="$PLIES" -v bullet=1 -v bots=1 -f "$DIR/gamebank.awk" "$OUT" > "$TSV.tmp" && mv "$TSV.tmp" "$TSV"
  echo "Tabelle: $TSV ($(wc -l < "$TSV" | tr -d ' ') Partien)" >&2
fi
