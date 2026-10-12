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
#                     downloaded into it (about 29 GB each).
#                     Without --archive the file is streamed from the internet.
#   --delete-archive  delete each monthly file as soon as its bank table is built and
#                     verified (--loeschen). Without this option the script asks once at the
#                     start (only in a terminal). Without a terminal nothing is deleted.
#   --keep-archive    never delete monthly files (--behalten)
#   --with-bullet     include bullet games (--mit-bullet, default: without)
#   --jobs N          parallel processes (--teile, default: CPU cores minus one, at most 8)
#   --plain           no animation, plain output (also: REPERTOIRE_PLAIN=1)

set -e -o pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/animation.sh"
[ $# -lt 2 ] && { sed -n '2,21p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
BANK="$1"; shift
MONATE=""; ARCHIV=""; BULLET=0; TEILE=""; LOESCHEN=""
while [ $# -gt 0 ]; do
  case "$1" in
    --archive|--archiv) ARCHIV="$2"; shift 2;;
    --delete-archive|--loeschen) LOESCHEN=1; shift;;
    --keep-archive|--behalten) LOESCHEN=0; shift;;
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

# Monatsdateien nach dem Bauen löschen? Das wird zu Beginn geklärt, damit der Lauf danach allein durchläuft.
if [ -n "$ARCHIV" ] && [ -z "$LOESCHEN" ]; then
  VORHANDEN=(); for M in $MONATE; do f="$ARCHIV/lichess_db_standard_rated_${M}.pgn.zst"; [ -s "$f" ] && VORHANDEN+=("$f"); done
  if [ -t 0 ] && [ -t 2 ]; then
    if [ ${#VORHANDEN[@]} -gt 0 ]; then
      echo "Diese Monatsdateien liegen schon da:" >&2
      for f in "${VORHANDEN[@]}"; do echo "  $(du -h "$f" | cut -f1)  $f" >&2; done
      printf "Jede nach dem Bauen ihrer Partienbank Tabelle löschen? [J/n] " >&2; read -r antwort </dev/tty || antwort=n
      case "$antwort" in n|N|nein|Nein) LOESCHEN=0;; *) LOESCHEN=1;; esac
    else
      LOESCHEN=1; echo "Heruntergeladene Monatsdateien werden nach dem Bauen der Partienbank gelöscht (--keep-archive verhindert das)." >&2
    fi
  else
    LOESCHEN=0
  fi
fi

# Monatsdatei löschen, aber nur wenn die Bankdatei des Monats heil ist
aufraeumen() {
  [ "$LOESCHEN" = 1 ] && [ -n "$ARCHIV" ] || return 0
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
  aufraeumen "$M"
done
