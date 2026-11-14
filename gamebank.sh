#!/bin/bash
# Game bank: turns Lichess monthly files once into compact tables of all games
# (no bullet, no bots, every opening, every rating range). After that every
# analysis only searches these tables instead of reading the monthly file again.
# repertoire.sh calls this automatically; use it directly to fill the bank in advance.
#
#   bash gamebank.sh 2026-07 2026-08 2026-09
#   bash gamebank.sh 2026-09 --keep-raw --data ~/my-chess-data
#
# Every month becomes FOLDER/bank/lichess_YYYY-MM.tsv.zst. Existing months are skipped.
#
# Options (German names in brackets work as well):
#   --data FOLDER     where the bank (FOLDER/bank) and the downloads (FOLDER/download) live
#                     (--daten, default ~/lichess-data). A missing month is downloaded once
#                     (about 29 GB), resumable: rerun the same command after an interruption.
#   --keep-raw        keep the monthly file after its table is built (--rohdaten-behalten).
#                     Default: it is deleted once the table is built and verified.
#   --with-bullet     include bullet games (--mit-bullet, default: without)
#   --jobs N          parallel processes (--teile, default: CPU cores minus one, at most 10)
#   --plain           no animation, plain output (also: REPERTOIRE_PLAIN=1)

set -e -o pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/animation.sh"
hilfe() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; }
[ $# -lt 1 ] && { hilfe; exit 1; }
MONATE=""; DATEN="$HOME/lichess-data"; BANK=""; ARCHIV=""; BULLET=0; TEILE=""; LOESCHEN=1
while [ $# -gt 0 ]; do
  case "$1" in
    --data|--daten) DATEN="$2"; shift 2;;
    --keep-raw|--rohdaten-behalten) LOESCHEN=0; shift;;
    --bank) BANK="$2"; shift 2;;                  # internal: repertoire.sh passes its folders
    --archive|--archiv) ARCHIV="$2"; shift 2;;
    --delete-archive|--loeschen) LOESCHEN=1; shift;;
    --keep-archive|--behalten) LOESCHEN=0; shift;;
    -h|--help|--hilfe) hilfe; exit 0;;
    --with-bullet|--mit-bullet) BULLET=1; shift;;
    --jobs|--teile) TEILE="$2"; shift 2;;
    --plain) export REPERTOIRE_PLAIN=1; shift;;
    [0-9][0-9][0-9][0-9]-[0-9][0-9]) MONATE="$MONATE $1"; shift;;
    *) echo "Unknown option: $1"; exit 1;;
  esac
done
for p in zstd python3 mkfifo; do command -v $p >/dev/null 2>&1 || { echo "$p fehlt"; exit 1; }; done
AWK=awk; command -v gawk >/dev/null 2>&1 && AWK=gawk; command -v mawk >/dev/null 2>&1 && AWK=mawk
if [ -z "$TEILE" ]; then
  KERNE=$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 2)
  TEILE=$((KERNE - 1)); [ "$TEILE" -lt 1 ] && TEILE=1; [ "$TEILE" -gt 10 ] && TEILE=10
fi
[ -z "$BANK" ] && BANK="$DATEN/bank"; [ -z "$ARCHIV" ] && ARCHIV="$DATEN/download"
mkdir -p "$BANK" "$ARCHIV"


# Monatsdatei löschen, aber nur wenn die Bankdatei des Monats heil ist
aufraeumen() {
  [ "$LOESCHEN" = 1 ] || return 0
  local q="$ARCHIV/lichess_db_standard_rated_$1.pgn.zst" g
  [ -f "$q" ] || return 0
  if zstd -tq "$BANK/lichess_$1.tsv.zst" 2>/dev/null; then
    g=$(du -h "$q" | cut -f1); rm -f "$q" && echo "Partienbank $1: Monatsdatei gelöscht, $g frei"
  else
    echo "Partienbank $1: Bankdatei besteht die Prüfung nicht, die Monatsdatei bleibt liegen"
  fi
}

for M in $MONATE; do
  ZIEL="$BANK/lichess_$M.tsv.zst"
  [ -s "$ZIEL" ] && { echo "Partienbank $M: schon vorhanden."; aufraeumen "$M"; continue; }
  URL="https://database.lichess.org/standard/lichess_db_standard_rated_${M}.pgn.zst"
  QUELLE="$ARCHIV/lichess_db_standard_rated_${M}.pgn.zst"
  if [ ! -s "$QUELLE" ]; then
    echo "Partienbank $M: lade Monatsdatei nach $QUELLE (etwa 29 GB, abgebrochene Downloads werden fortgesetzt)"
    laden "$URL" "$QUELLE.part" "Download $M" || { echo "$M: Download fehlgeschlagen. Nochmal starten setzt ihn fort."; exit 1; }
    mv "$QUELLE.part" "$QUELLE"
  fi
  echo "Partienbank $M: baue Tabelle aller Partien mit $TEILE Prozessen"
  TMP=$(mktemp -d "$BANK/.bau_${M}_XXXX")
  PIDS=""; ZIELE=""
  for i in $(seq 0 $((TEILE - 1))); do
    mkfifo "$TMP/f$i"
    ( LC_ALL=C "$AWK" -v plies=40 -v bullet="$BULLET" -f "$DIR/gamebank.awk" < "$TMP/f$i" | zstd -q -5 > "$TMP/t$i.zst" ) &
    PIDS="$PIDS $!"; ZIELE="$ZIELE $TMP/f$i"
  done
  START=$(date +%s)
  if anim_an; then
    anim_start "Partienbank $M" --pv "$TMP/fortschritt"
    strom_datei "$QUELLE" "$TMP/fortschritt" | zstd -dc | python3 "$DIR/verteilen.py" "$TEILE" $ZIELE
  else
    if command -v pv >/dev/null 2>&1; then pv "$QUELLE" | zstd -dc; else zstd -dc "$QUELLE"; fi | python3 "$DIR/verteilen.py" "$TEILE" $ZIELE
  fi
  FEHLER=0; for p in $PIDS; do wait "$p" || FEHLER=1; done
  anim_stopp
  [ "$FEHLER" = 1 ] && { echo "Partienbank $M: Fehler beim Umwandeln."; rm -rf "$TMP"; exit 1; }
  cat "$TMP"/t*.zst > "$ZIEL.tmp" && mv "$ZIEL.tmp" "$ZIEL"; rm -rf "$TMP"
  echo "Partienbank $M: fertig nach $(( ($(date +%s) - START) / 60 )) Min., $(du -h "$ZIEL" | cut -f1)"
  aufraeumen "$M"
done
