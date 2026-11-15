#!/bin/bash
# Builds an opening repertoire with one command.
#
#   bash repertoire.sh white "1. e4"
#   bash repertoire.sh black "1. d4 d5" --elo 1600-2000
#   bash repertoire.sh white "1. e4" --months 3
#   bash repertoire.sh white @zuege.txt           (long start moves in a text file, move numbers optional)
#
# Options (German names in brackets work as well):
#   --elo FROM-TO        rating range of both players             (default 1800-2499)
#   --month YYYY-MM      Lichess month (--monat)                  (default: last full month)
#                        several months: --month 2026-07..2026-09
#   --months N           the last N full months (--monate), e.g. --months 3
#   --data FOLDER        where the game bank and the downloads live (--daten)
#                        (default ~/lichess-data). Every month is downloaded once (about 29 GB,
#                        resumable: rerun the same command after an interruption) and turned into a
#                        compact table of all games (about 5 GB per month) in FOLDER/bank. After that every
#                        further analysis with any starting moves and rating range takes only
#                        seconds per month.
#   --keep-raw           keep the 29 GB monthly file after its bank table is built (--rohdaten-behalten)
#                        (default: it is deleted once the table is built and verified; the bank stays)
#   --file FILE          your own Lichess file (.pgn or .pgn.zst) instead of the download (--datei)
#   --name NAME          name of the repertoire                     (default from colour and moves)
#   --out FOLDER         where the finished files go                (--ausgabe, default: folder "repertoires"
#                        next to this tool folder). Working files go to FOLDER/arbeit/NAME.
#   --repertoire PGN     your own repertoire, its moves get marked
#   --quick              quick trial run with low Stockfish depth (--schnell)
#   --plain              no animation, plain output (also automatic when the output goes to a file)
#   --notation de        German piece letters (S, L, T, D) in chapter names and comments
#                        instead of English (N, B, R, Q). The moves stay standard PGN.
#
# Colour: white or black (weiss or schwarz work as well).
# The finished files (repertoire, quickstart, structures) land in the results folder. Games,
# Stockfish cache and konfiguration.json stay in the working folder FOLDER/arbeit/NAME.
# Running again with the same arguments reuses them and only computes what is missing. For
# fine tuning edit konfiguration.json there and run again.

set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/animation.sh"
hilfe() { sed -n '2,36p' "$0" | sed 's/^# \{0,1\}//'; }

[ $# -lt 2 ] && { hilfe; exit 1; }
START_ARG="$2"
case "$START_ARG" in   # @datei.txt: die Startzüge stehen in einer Textdatei (Zugnummern sind optional)
  @*) F="${START_ARG#@}"; [ -f "$F" ] || { echo "Datei mit Startzügen nicht gefunden: $F"; exit 1; }; START_ARG=$(tr '\n' ' ' < "$F");;
esac
FARBE="$1"; START=$(printf '%s' "$START_ARG" | sed -E 's/([0-9]+)\.([^ .])/\1. \2/g'); shift 2
ELO="1800-2499"; MONAT=""; ANZAHL=""; ARCHIV=""; BANK=""; DATEI=""; NAME=""; ERG=""; REP=""; SCHNELL=""; NOTATION="en"; LOESCHEN=""; DATEN=""
while [ $# -gt 0 ]; do
  case "$1" in
    --elo) ELO="$2"; shift 2;;
    --month|--monat) MONAT="$2"; shift 2;;
    --months|--monate) ANZAHL="$2"; shift 2;;
    --data|--daten) DATEN="$2"; shift 2;;
    --keep-raw|--rohdaten-behalten) LOESCHEN="--keep-archive"; shift;;
    --archive|--archiv) ARCHIV="$2"; shift 2;;
    --bank|--gamebank|--partienbank) BANK="$2"; shift 2;;
    --delete-archive|--loeschen) LOESCHEN="--delete-archive"; shift;;
    --keep-archive|--behalten) LOESCHEN="--keep-archive"; shift;;
    --file|--datei) DATEI="$2"; shift 2;;
    --name) NAME="$2"; shift 2;;
    --out|--ausgabe) ERG="$2"; ERG_GEWAEHLT=1; shift 2;;
    --repertoire) REP="$2"; shift 2;;
    --quick|--schnell) SCHNELL=1; shift;;
    --notation) NOTATION="$2"; shift 2;;
    --plain) export REPERTOIRE_PLAIN=1; shift;;
    -h|--help|--hilfe) hilfe; exit 0;;
    *) echo "Unknown option: $1 (bash repertoire.sh --help shows all options)"; exit 1;;
  esac
done
# One data folder: bank and downloads. The old --bank/--archive still win when given.
DATEN="${DATEN:-$HOME/lichess-data}"
[ -z "$BANK" ] && BANK="$DATEN/bank"
[ -z "$ARCHIV" ] && ARCHIV="$DATEN/download"
[ -z "$LOESCHEN" ] && LOESCHEN="--delete-archive"
case "$FARBE" in
  weiss|weiß|white|w) FARBE=weiss;;
  schwarz|black|b|s) FARBE=schwarz;;
  *) echo "Colour must be white or black (weiss or schwarz)"; exit 1;;
esac
if [ -n "$MONAT" ] && ! [[ "$MONAT" =~ ^[0-9]{4}-[0-9]{2}(\.\.[0-9]{4}-[0-9]{2})?$ ]]; then
  echo "--month erwartet JJJJ-MM (z. B. 2026-08) oder JJJJ-MM..JJJJ-MM."
  [[ "$MONAT" =~ ^[0-9]+$ ]] && echo "Meintest du --months $MONAT (die letzten $MONAT Monate)?"
  exit 1
fi
if [ -n "$ANZAHL" ] && ! [[ "$ANZAHL" =~ ^[0-9]+$ ]]; then echo "--months erwartet eine Zahl, z. B. --months 3."; exit 1; fi
ELO_MIN="${ELO%%-*}"; ELO_MAX="${ELO##*-}"
if [ -z "$NAME" ]; then
  ZUEGE="$(printf '%s' "$START" | tr -cd 'A-Za-z0-9 ' | tr -s ' ' '_')"
  NAME="$( [ "$FARBE" = weiss ] && echo white || echo black )_$ZUEGE"
  [ ! -d "$PWD/$NAME" ] && [ -d "$PWD/${FARBE}_$ZUEGE" ] && NAME="${FARBE}_$ZUEGE"   # Ordner aus früheren Versionen
fi
# Ergebnisordner (fertige Dateien) und Arbeitsordner (Partien, Zwischenspeicher, Konfiguration)
ERG="${ERG:-$(dirname "$DIR")/repertoires}"; ERG="${ERG/#\~/$HOME}"
case "$ERG" in /*) ;; *) ERG="$PWD/$ERG";; esac
OUT="$ERG/arbeit/$NAME"
[ ! -f "$OUT/konfiguration.json" ] && [ -f "$PWD/$NAME/konfiguration.json" ] && OUT="$PWD/$NAME"   # Ordner aus früheren Versionen bleibt in Benutzung

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

# Startzüge prüfen, bevor etwas geladen wird
"$PY" - "$START" <<'PYEOF' || exit 1
import sys, re, chess
b = chess.Board()
for t in sys.argv[1].split():
    t = re.sub(r"^\d+\.+", "", t)
    if not t: continue
    try: b.push_san(t)
    except ValueError:
        farbe = "Weiß" if b.turn else "Schwarz"
        moegl = ", ".join(sorted(b.san(m) for m in b.legal_moves))
        print(f"Startzüge ungültig: {t} ist für {farbe} hier nicht möglich.")
        print(f"Möglich wären: {moegl}")
        print("Züge in englischer Notation: N Springer, B Läufer, R Turm, Q Dame, K König.")
        sys.exit(1)
PYEOF

mkdir -p "$OUT"
echo "Repertoire: $FARBE, Startzüge \"$START\", Elo $ELO_MIN bis $ELO_MAX"
echo "Arbeitsordner: $OUT"

# 1. Partien holen und filtern
filtern() {  # $1 Quelle (-i DATEI oder -m MONAT), $2 Wert, $3 Ziel ohne Endung, $4 Titel
  REPERTOIRE_TITEL="${4:-Filtern}" bash "$DIR/lichess_filter.sh" -s "$START" "$1" "$2" -o "$3.pgn" --tsv "$3.tsv" --elo-min "$ELO_MIN" --elo-max "$ELO_MAX"
}
if [ -n "$DATEI" ]; then
  if [ -s "$OUT/partien.tsv" ]; then
    echo "Partien schon vorhanden ($OUT/partien.tsv). Zum Neuladen die Datei löschen."
  else
    filtern -i "$DATEI" "$OUT/partien"
  fi
else
  # Liste der Monate bestimmen: einzelner Monat, Bereich VON..BIS oder die letzten N
  MONATE=$(python3 - "$MONAT" "$ANZAHL" <<'PYEOF'
import sys, re, datetime as d
arg, anzahl = sys.argv[1], sys.argv[2]
def plus(y, m, k):
    m += k; return y + (m - 1) // 12, (m - 1) % 12 + 1
t = d.date.today().replace(day=1) - d.timedelta(days=1)
if anzahl:
    n = int(anzahl); out = [plus(t.year, t.month, -i) for i in range(n - 1, -1, -1)]
elif ".." in arg:
    a, b = [tuple(map(int, x.split("-"))) for x in arg.split("..")]
    out = []
    while a <= b: out.append(a); a = plus(*a, 1)
elif arg:
    out = [tuple(map(int, arg.split("-")))]
else:
    out = [(t.year, t.month)]
print(" ".join(f"{y:04d}-{m:02d}" for y, m in out))
PYEOF
  ) || { echo "Monat bitte als JJJJ-MM, JJJJ-MM..JJJJ-MM oder mit --monate N angeben"; exit 1; }
  set -- $MONATE; echo "Monate: $* ($# insgesamt)"
  mkdir -p "$OUT/monate"
  # Startzüge ohne Zugnummern, so wie sie in der Tabelle stehen
  AWK=awk; command -v gawk >/dev/null 2>&1 && AWK=gawk; command -v mawk >/dev/null 2>&1 && AWK=mawk
  STARTZ=$(printf '%s' "$START" | sed -E 's/[0-9]+\.+ ?/ /g' | tr -s ' ' | sed -E 's/^ //; s/ $//')
  bash "$DIR/gamebank.sh" $MONATE --bank "$BANK" --archive "$ARCHIV" "$LOESCHEN"
  for M in $MONATE; do
    ZIEL="$OUT/monate/partien_${M}_elo${ELO_MIN}-${ELO_MAX}"
    if [ -s "$ZIEL.tsv" ]; then echo "$M: schon gefiltert, wird wiederverwendet."; continue; fi
    echo "$M: suche in der Partienbank"
    ANIM=""; anim_an && { ANIM=1; : > "$ZIEL.fortschritt"; anim_start "Suche $M" --pv "$ZIEL.fortschritt"; }
    if [ -n "$ANIM" ]; then
      strom_datei "$BANK/lichess_$M.tsv.zst" "$ZIEL.fortschritt"
    else
      cat "$BANK/lichess_$M.tsv.zst"
    fi | zstd -dc | LC_ALL=C "$AWK" -F'\t' -v start="$STARTZ" -v emin="$ELO_MIN" -v emax="$ELO_MAX" '
      BEGIN { s = start " "; L = length(s) }
      substr($12 " ", 1, L) == s { a = $4 + 0; b = $5 + 0; lo = (a < b ? a : b); hi = (a < b ? b : a)
                                   if (lo >= emin && hi <= emax) print }' > "$ZIEL.tsv.tmp"
    anim_stopp; rm -f "$ZIEL.fortschritt"; mv "$ZIEL.tsv.tmp" "$ZIEL.tsv"
    echo "$M: $(wc -l < "$ZIEL.tsv" | tr -d ' ') Partien"
  done
  # Tabelle aus allen gewünschten Monaten neu zusammensetzen
  for M in $MONATE; do cat "$OUT/monate/partien_${M}_elo${ELO_MIN}-${ELO_MAX}.tsv"; done > "$OUT/partien.tsv.tmp" && mv "$OUT/partien.tsv.tmp" "$OUT/partien.tsv"
  echo "Zusammen: $(wc -l < "$OUT/partien.tsv" | tr -d ' ') Partien aus $# Monaten"
fi

# 2. Konfiguration anlegen (beim ersten Mal) und den Ergebnisordner eintragen
if [ ! -f "$OUT/konfiguration.json" ]; then
  "$PY" - "$OUT/konfiguration.json" "$FARBE" "$START" "$NAME" "$REP" "$NOTATION" <<'PYEOF'
import json, os, sys
pfad, farbe, start, name, rep, notation = sys.argv[1:]
c = {"titel": f"Repertoire {farbe} {start}", "farbe": farbe, "start": start,
     "daten": "partien.tsv", "ausgabe": name + ".pgn", "prozesse": max(1, (os.cpu_count() or 2) - 1),
     "notation": "de" if notation.lower().startswith("de") else "en"}
if farbe == "schwarz": c["erste_antworten"] = 5
if rep: c["repertoire_pgn"] = os.path.abspath(rep)
json.dump(c, open(pfad, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
PYEOF
fi
"$PY" - "$OUT/konfiguration.json" "$ERG" "${ERG_GEWAEHLT:-}" <<'PYEOF'
import json, sys
pfad, erg, gewaehlt = sys.argv[1:]
c = json.load(open(pfad, encoding="utf-8"))
if gewaehlt or "ergebnis" not in c:                      # --out überschreibt, sonst nur nachtragen
    c["ergebnis"] = erg
    json.dump(c, open(pfad, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
PYEOF

# 3. Repertoire bauen
REPERTOIRE_SCHNELL="$SCHNELL" "$PY" "$DIR/repertoire.py" "$OUT/konfiguration.json"
echo
ERGEBNIS=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("ergebnis",""))' "$OUT/konfiguration.json")
echo "Fertig. Deine Dateien liegen in: $ERGEBNIS"
echo "  $NAME.pgn              Repertoire"
echo "  ${NAME}_quickstart.pgn   wahrscheinlichste Linien zum Üben"
