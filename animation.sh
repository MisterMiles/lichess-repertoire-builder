# Hilfsfunktionen für die Springer Animation in den Bash Skripten (wird mit source geladen).
# Ohne Terminal, ohne python3 oder pv, oder mit REPERTOIRE_PLAIN=1 bleibt die Ausgabe schlicht.

ANIM_PY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/animation.py"
LADEN_PY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/laden_parallel.py"
ANIM_PID=""

anim_an() {
  [ -z "$REPERTOIRE_PLAIN" ] && [ -t 2 ] && [ "$TERM" != "dumb" ] \
    && command -v python3 >/dev/null 2>&1 && command -v pv >/dev/null 2>&1
}
dateigroesse() { python3 -c 'import os, sys; print(os.path.getsize(sys.argv[1]))' "$1"; }
urlgroesse() { curl -sIL "$1" | tr -d '\r' | awk 'tolower($1) == "content-length:" { n = $2 } END { print n + 0 }'; }
anim_start() { python3 "$ANIM_PY" "$@" </dev/null >/dev/null & ANIM_PID=$!; }   # nur stderr, damit keine Pipe offen bleibt
anim_stopp() {
  if [ -n "$ANIM_PID" ]; then kill "$ANIM_PID" 2>/dev/null; wait "$ANIM_PID" 2>/dev/null; ANIM_PID=""; fi
  return 0
}

# Download in eine Datei, abgebrochene Downloads werden fortgesetzt.   laden URL ZIEL TITEL
laden() {
  local g n="${REPERTOIRE_VERBINDUNGEN:-4}" rc
  g=$(urlgroesse "$1")
  # Mehrere Verbindungen, weil Lichess jede einzelne drosselt. REPERTOIRE_VERBINDUNGEN=1 schaltet das ab.
  if [ "$g" -gt 0 ] && { [ "$n" -gt 1 ] || [ -e "$2.blocks" ]; }; then
    anim_an && anim_start "$3" --groesse "$2" --gesamt "$g"
    python3 "$LADEN_PY" "$1" "$2" "$g" "$n"; rc=$?
    anim_stopp; return $rc
  fi
  if anim_an; then
    anim_start "$3" --groesse "$2" --gesamt "$(urlgroesse "$1")"
    curl -sfL -C - --retry 5 --retry-delay 10 -o "$2" "$1"; local rc=$?
    anim_stopp; return $rc
  fi
  curl -fL -C - --retry 5 --retry-delay 10 -# -o "$2" "$1"
}

# Datei als Datenstrom auf stdout, mit Fortschritt in einer pv Datei.   strom_datei DATEI PVDATEI
# Die Animation dazu startet der Aufrufer:  anim_start TITEL --pv PVDATEI  ...  anim_stopp
strom_datei() { pv -n -i 0.5 -s "$(dateigroesse "$1")" "$1" 2>"$2"; }

trap anim_stopp EXIT
