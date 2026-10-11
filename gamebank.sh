#!/bin/bash
# Game bank: turns Lichess monthly files once into compact tables of all games
# (no bullet, no bots, every opening, every rating range). After that every
# analysis only searches these tables instead of reading the monthly file again.
#
#   bash gamebank.sh FOLDER 2026-07 2026-08 2026-09
#   bash gamebank.sh FOLDER 2026-09 --archive ~/lichess
#
# Every month becomes FOLDER/lichess_YYYY-MM.tsv.zst. Existing months are skipped.
#
# Options (German names in brackets work as well):
#   --archive FOLDER  read the monthly files from there (--archiv). A missing one is
#                     downloaded into it and kept (about 29 GB each).
#                     Without --archive the file is streamed from the internet.
#   --with-bullet     include bullet games (--mit-bullet, default: without)
#   --jobs N          parallel processes (--teile, default: CPU cores minus one, at most 8)
#   --plain           no animation, plain output (also: REPERTOIRE_PLAIN=1)

set -e -o pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/animation.sh"
[ $# -lt 2 ] && { sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
BANK="$1"; shift
MONATE=""; ARCHIV=""; BULLET=0; TEILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --archive|--archiv) ARCHIV="$2"; shift 2;;
    --with-bullet|--mit-bullet) BULLET=1; shift;;
    --jobs|--teile) TEILE="$2"; shift 2;;
    --plain) export REPERTOIRE_PLAIN=1; shift;;
    [0-9][0-9][0-9][0-9]-[0-9][0-9]) MONATE="$MONATE $1"; shift;;
    *) echo "Unknown option: $1"; exit 1;;
  esac
done
for p in zstd tee mkfifo; do command -v $p >/dev/null 2>&1 || { echo "$p fehlt"; exit 1; }; done
AWK=awk; command -v gawk >/dev/null 2>&1 && AWK=gawk; command -v mawk >/dev/null 2>&1 && AWK=mawk
if [ -z "$TEILE" ]; then
  KERNE=$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 2)
  TEILE=$((KERNE - 1)); [ "$TEILE" -lt 1 ] && TEILE=1; [ "$TEILE" -gt 8 ] && TEILE=8
fi
mkdir -p "$BANK"; [ -n "$ARCHIV" ] && mkdir -p "$ARCHIV"

for M in $MONATE; do
  ZIEL="$BANK/lichess_$M.tsv.zst"
  [ -s "$ZIEL" ] && { echo "Partienbank $M: schon vorhanden."; continue; }
  URL="https://database.lichess.org/standard/lichess_db_standard_rated_${M}.pgn.zst"
  QUELLE=""
  if [ -n "$ARCHIV" ]; then
    QUELLE="$ARCHIV/lichess_db_standard_rated_${M}.pgn.zst"
    if [ ! -s "$QUELLE" ]; then
      echo "Partienbank $M: lade Monatsdatei nach $QUELLE (etwa 29 GB, abgebrochene Downloads werden fortgesetzt)"
      laden "$URL" "$QUELLE.part" "Download $M" || { echo "$M: Download fehlgeschlagen. Nochmal starten setzt ihn fort."; exit 1; }
      mv "$QUELLE.part" "$QUELLE"
    fi
  fi
  echo "Partienbank $M: baue Tabelle aller Partien mit $TEILE Prozessen$( [ -z "$QUELLE" ] && echo ", die Monatsdatei (etwa 29 GB) wird gestreamt")"
  TMP=$(mktemp -d "$BANK/.bau_${M}_XXXX")
  PIDS=""; ZIELE=""
  for i in $(seq 0 $((TEILE - 1))); do
    mkfifo "$TMP/f$i"
    ( LC_ALL=C "$AWK" -v plies=40 -v bullet="$BULLET" -v teil="$i" -v teile="$TEILE" -f "$DIR/gamebank.awk" < "$TMP/f$i" | zstd -q -5 > "$TMP/t$i.zst" ) &
    PIDS="$PIDS $!"; [ "$i" -gt 0 ] && ZIELE="$ZIELE $TMP/f$i"
  done
  START=$(date +%s)
  if anim_an; then
    anim_start "Partienbank $M" --pv "$TMP/fortschritt"
    if [ -n "$QUELLE" ]; then strom_datei "$QUELLE" "$TMP/fortschritt"; else strom_url "$URL" "$TMP/fortschritt"; fi | zstd -dc | tee $ZIELE > "$TMP/f0"
  elif [ -n "$QUELLE" ]; then
    if command -v pv >/dev/null 2>&1; then pv "$QUELLE" | zstd -dc; else zstd -dc "$QUELLE"; fi | tee $ZIELE > "$TMP/f0"
  else
    curl -fL --retry 5 --retry-delay 10 -# "$URL" | zstd -dc | tee $ZIELE > "$TMP/f0"
  fi
  FEHLER=0; for p in $PIDS; do wait "$p" || FEHLER=1; done
  anim_stopp
  [ "$FEHLER" = 1 ] && { echo "Partienbank $M: Fehler beim Umwandeln."; rm -rf "$TMP"; exit 1; }
  cat "$TMP"/t*.zst > "$ZIEL.tmp" && mv "$ZIEL.tmp" "$ZIEL"; rm -rf "$TMP"
  echo "Partienbank $M: fertig nach $(( ($(date +%s) - START) / 60 )) Min., $(du -h "$ZIEL" | cut -f1)"
done
