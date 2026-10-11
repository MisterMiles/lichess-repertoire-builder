#!/bin/bash
# Partienbank: wandelt Lichess Monatsdateien einmalig in kompakte Tabellen aller
# Partien (ohne Bullet und Bots, alle Eröffnungen, alle Elo Bereiche). Jede
# Analyse sucht danach nur noch in diesen Tabellen, statt die Monatsdatei neu
# zu lesen.
#
#   bash partienbank.sh ORDNER 2026-07 2026-08 2026-09
#   bash partienbank.sh ORDNER 2026-09 --archiv ~/lichess
#
# Je Monat entsteht ORDNER/lichess_JJJJ-MM.tsv.zst. Schon vorhandene Monate
# werden übersprungen.
#
# Optionen:
#   --archiv ORDNER   Monatsdateien von dort lesen. Fehlt eine, wird sie dorthin
#                     geladen und bleibt gespeichert (je etwa 29 GB).
#                     Ohne --archiv wird direkt aus dem Internet gestreamt.
#   --mit-bullet      Bullet Partien mit aufnehmen (Standard: ohne)
#   --teile N         parallele Prozesse (Standard: CPU Kerne minus eins, höchstens 8)

set -e -o pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ $# -lt 2 ] && { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
BANK="$1"; shift
MONATE=""; ARCHIV=""; BULLET=0; TEILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --archiv) ARCHIV="$2"; shift 2;;
    --mit-bullet) BULLET=1; shift;;
    --teile) TEILE="$2"; shift 2;;
    [0-9][0-9][0-9][0-9]-[0-9][0-9]) MONATE="$MONATE $1"; shift;;
    *) echo "Unbekannte Angabe: $1"; exit 1;;
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
      curl -fL -C - --retry 5 --retry-delay 10 -# -o "$QUELLE.part" "$URL" || { echo "$M: Download fehlgeschlagen. Nochmal starten setzt ihn fort."; exit 1; }
      mv "$QUELLE.part" "$QUELLE"
    fi
  fi
  echo "Partienbank $M: baue Tabelle aller Partien mit $TEILE Prozessen$( [ -z "$QUELLE" ] && echo ", die Monatsdatei (etwa 29 GB) wird gestreamt")"
  TMP=$(mktemp -d "$BANK/.bau_${M}_XXXX")
  PIDS=""; ZIELE=""
  for i in $(seq 0 $((TEILE - 1))); do
    mkfifo "$TMP/f$i"
    ( LC_ALL=C "$AWK" -v plies=40 -v bullet="$BULLET" -v teil="$i" -v teile="$TEILE" -f "$DIR/partienbank.awk" < "$TMP/f$i" | zstd -q -5 > "$TMP/t$i.zst" ) &
    PIDS="$PIDS $!"; [ "$i" -gt 0 ] && ZIELE="$ZIELE $TMP/f$i"
  done
  START=$(date +%s)
  if [ -n "$QUELLE" ]; then
    if command -v pv >/dev/null 2>&1; then pv "$QUELLE" | zstd -dc; else zstd -dc "$QUELLE"; fi
  else
    curl -fL --retry 5 --retry-delay 10 -# "$URL" | zstd -dc
  fi | tee $ZIELE > "$TMP/f0"
  FEHLER=0; for p in $PIDS; do wait "$p" || FEHLER=1; done
  [ "$FEHLER" = 1 ] && { echo "Partienbank $M: Fehler beim Umwandeln."; rm -rf "$TMP"; exit 1; }
  cat "$TMP"/t*.zst > "$ZIEL.tmp" && mv "$ZIEL.tmp" "$ZIEL"; rm -rf "$TMP"
  echo "Partienbank $M: fertig nach $(( ($(date +%s) - START) / 60 )) Min., $(du -h "$ZIEL" | cut -f1)"
done
