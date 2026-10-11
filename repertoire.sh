#!/bin/bash
# Startskript: baut mit einem Befehl ein Eröffnungsrepertoire.
#
#   ./repertoire.sh weiss "1. e4"
#   ./repertoire.sh schwarz "1. d4 d5" --elo 1600-2000
#
# Optionen:
#   --elo VON-BIS     Elo Bereich beider Spieler            (Standard 1800-2499)
#   --monat JJJJ-MM   Lichess Monat                          (Standard: letzter voller Monat)
#   --datei DATEI     eigene Lichess Datei (.pgn oder .pgn.zst) statt Download
#   --name NAME       Name des Ordners für die Ergebnisse     (Standard aus Farbe und Zügen)
#   --repertoire PGN  eigenes Repertoire, dessen Züge markiert werden
#   --schnell         schneller Probelauf mit geringer Stockfish Tiefe
#
# Alles landet in einem Ordner mit dem Namen des Repertoires. Ein zweiter Aufruf
# mit gleichen Angaben nutzt die schon geladenen Partien und rechnet nur Neues.
# Feineinstellungen: im Ordner konfiguration.json bearbeiten und erneut starten.

set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
hilfe() { sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; }

[ $# -lt 2 ] && { hilfe; exit 1; }
FARBE="$1"; START="$2"; shift 2
ELO="1800-2499"; MONAT=""; DATEI=""; NAME=""; REP=""; SCHNELL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --elo) ELO="$2"; shift 2;;
    --monat) MONAT="$2"; shift 2;;
    --datei) DATEI="$2"; shift 2;;
    --name) NAME="$2"; shift 2;;
    --repertoire) REP="$2"; shift 2;;
    --schnell) SCHNELL=1; shift;;
    -h|--help) hilfe; exit 0;;
    *) echo "Unbekannte Option: $1"; exit 1;;
  esac
done
case "$FARBE" in
  weiss|weiß|white|w) FARBE=weiss;;
  schwarz|black|b|s) FARBE=schwarz;;
  *) echo "Farbe bitte als weiss oder schwarz angeben"; exit 1;;
esac
ELO_MIN="${ELO%%-*}"; ELO_MAX="${ELO##*-}"
[ -z "$NAME" ] && NAME="${FARBE}_$(printf '%s' "$START" | tr -cd 'A-Za-z0-9 ' | tr -s ' ' '_')"
OUT="$PWD/$NAME"

# Benötigte Programme prüfen
fehlt=""
command -v stockfish >/dev/null 2>&1 || fehlt="$fehlt stockfish"
command -v python3 >/dev/null 2>&1 || fehlt="$fehlt python3"
if [ -z "$DATEI" ] || [[ "$DATEI" == *.zst ]]; then command -v zstd >/dev/null 2>&1 || fehlt="$fehlt zstd"; fi
if [ -z "$DATEI" ]; then command -v curl >/dev/null 2>&1 || fehlt="$fehlt curl"; fi
if [ -n "$fehlt" ]; then
  echo "Es fehlen noch Programme:$fehlt"
  if [ "$(uname)" = "Darwin" ]; then echo "Installieren mit:  brew install$fehlt pv mawk"
  else echo "Installieren mit:  sudo apt install$fehlt pv mawk python3-venv"; fi
  exit 1
fi

# Python Umgebung mit python-chess (einmalig)
VENV="$HOME/.venv-repertoire"; PY="$VENV/bin/python"
if [ ! -x "$PY" ]; then
  echo "Richte einmalig eine Python Umgebung in $VENV ein ..."
  python3 -m venv "$VENV"
fi
"$PY" -c "import chess" 2>/dev/null || "$VENV/bin/pip" install -q chess

mkdir -p "$OUT"
echo "Repertoire: $FARBE, Startzüge \"$START\", Elo $ELO_MIN bis $ELO_MAX, Ordner $OUT"

# 1. Partien holen und filtern
if [ -s "$OUT/partien.tsv" ]; then
  echo "Partien schon vorhanden ($OUT/partien.tsv). Zum Neuladen die Datei löschen."
elif [ -n "$DATEI" ]; then
  bash "$DIR/lichess_filter.sh" -s "$START" -i "$DATEI" -o "$OUT/partien.pgn" --tsv "$OUT/partien.tsv" --elo-min "$ELO_MIN" --elo-max "$ELO_MAX"
else
  [ -z "$MONAT" ] && MONAT=$(python3 -c "import datetime as d; t=d.date.today().replace(day=1)-d.timedelta(days=1); print(t.strftime('%Y-%m'))")
  echo "Lade Lichess Partien aus $MONAT. Die Datei (etwa 29 GB) wird gestreamt und nicht gespeichert."
  echo "Das dauert je nach Internetleitung 30 Minuten bis einige Stunden."
  bash "$DIR/lichess_filter.sh" -s "$START" -m "$MONAT" -o "$OUT/partien.pgn" --tsv "$OUT/partien.tsv" --elo-min "$ELO_MIN" --elo-max "$ELO_MAX"
fi

# 2. Konfiguration anlegen (nur beim ersten Mal)
if [ ! -f "$OUT/konfiguration.json" ]; then
  "$PY" - "$OUT/konfiguration.json" "$FARBE" "$START" "$NAME" "$REP" <<'PYEOF'
import json, os, sys
pfad, farbe, start, name, rep = sys.argv[1:]
c = {"titel": f"Repertoire {farbe} {start}", "farbe": farbe, "start": start,
     "daten": "partien.tsv", "ausgabe": name + ".pgn", "prozesse": max(1, (os.cpu_count() or 2) - 1)}
if farbe == "schwarz": c["erste_antworten"] = 5
if rep: c["repertoire_pgn"] = os.path.abspath(rep)
json.dump(c, open(pfad, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
PYEOF
fi

# 3. Repertoire bauen
REPERTOIRE_SCHNELL="$SCHNELL" "$PY" "$DIR/repertoire.py" "$OUT/konfiguration.json"
echo
echo "Fertig. Deine Dateien liegen in: $OUT"
echo "  $NAME.pgn              Repertoire"
echo "  ${NAME}_quickstart.pgn   wahrscheinlichste Linien zum Üben"
