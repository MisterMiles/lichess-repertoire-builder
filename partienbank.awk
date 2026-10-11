# Wandelt eine Lichess Monatsdatei (PGN Strom) in eine Tabelle aller Partien
# ohne Bullet, ohne Bots und ohne Partien ohne Elo. Spalten wie pgn_tabelle.awk:
#   Site, White, Black, WhiteElo, BlackElo, Result, Termination, TimeControl,
#   Date, Halbzüge gesamt, letzter Zug, erste N Halbzüge
# Aufruf: zstd -dc monat.pgn.zst | mawk -v plies=40 -f partienbank.awk > bank.tsv
# Optionen: -v bullet=1 behält Bullet, -v bots=1 behält Bot Partien,
#           -v teile=4 -v teil=0 bearbeitet nur jede vierte Partie (für parallele Läufe).
#
# Für Tempo werden Züge nur aus dem Anfang (erste N Halbzüge) und dem Ende
# (Zugzahl und letzter Zug) der Notation gelesen, nicht aus der ganzen Partie.
# Das Format ist auf die Lichess Monatsdateien zugeschnitten.

function val(s) { sub(/^\[[A-Za-z]+ "/, "", s); sub(/"\]\r?$/, "", s); return s }

function flush(   cut, head, n, a, i, x, k, out, tail, p, last, j, ganz) {
  if (!aktiv) return
  aktiv = 0
  if (skip || mv == "") return
  if (r != "1-0" && r != "0-1" && r != "1/2-1/2") return
  if (we !~ /^[0-9]+$/ || be !~ /^[0-9]+$/) return
  # Anfang: nur bis zum Zug nach den ersten N Halbzügen lesen, Kommentare und Zugnummern weg
  cut = index(mv, " " zugende ". ")
  ganz = (cut == 0)
  head = ganz ? mv : substr(mv, 1, cut)
  if (index(head, "{")) gsub(/\{[^}]*\} */, "", head)
  gsub(/[0-9]+\.(\.\.)? /, "", head)
  while (substr(head, length(head), 1) == " ") head = substr(head, 1, length(head) - 1)
  out = head; k = 0; last = ""
  if (ganz || plies % 2) {
    n = split(head, a, " ")
    if (ganz && n && index("0123456789*", substr(a[n], 1, 1))) {      # Ergebnis am Ende weg
      out = substr(head, 1, length(head) - length(a[n]))
      while (substr(out, length(out), 1) == " ") out = substr(out, 1, length(out) - 1)
      n--
    }
    if (ganz) { k = n; last = (n ? a[n] : "") }
    if (n > plies) { out = a[1]; for (i = 2; i <= plies; i++) out = out " " a[i] }
  }
  if (!ganz) {
    # Zugzahl und letzter Zug aus dem Ende der Notation
    tail = substr(mv, length(mv) - 500)
    i = index(tail, "}"); j = index(tail, "{")
    if (i > 0 && (j == 0 || i < j)) tail = substr(tail, i + 1)
    gsub(/\{[^}]*\}/, "", tail); sub(/\{.*$/, "", tail)
    n = split(tail, a, " "); p = -1
    for (i = 1; i <= n; i++) {
      x = a[i]
      if (x ~ /^[0-9]+\.\.\.$/) { p = 2 * (x + 0) - 1; continue }
      if (x ~ /^[0-9]+\.$/) { p = 2 * (x + 0) - 2; continue }
      if (p < 0 || index("0123456789*", substr(x, 1, 1))) continue
      p++; last = x
    }
    if (p > 0) k = p
  }
  print site "\t" w "\t" b "\t" we "\t" be "\t" r "\t" t "\t" tc "\t" dt "\t" k "\t" last "\t" out
}

BEGIN { if (plies == "") plies = 40; zugende = int((plies + 1) / 2) + 1 }
/^\[Event / {
  flush(); aktiv = 1; mv = ""
  site = w = b = we = be = r = t = tc = dt = ""
  g++
  skip = (teile > 1 && g % teile != teil) || (!bullet && index($0, "Bullet") > 0)
  next
}
skip { next }
/^\[/ {
  if (index($0, "Title \"BOT\"") && !bots) { skip = 1; next }
  key = substr($0, 2, index($0, " ") - 2)
  if (key == "Site") site = val($0)
  else if (key == "White") w = val($0)
  else if (key == "Black") b = val($0)
  else if (key == "WhiteElo") we = val($0)
  else if (key == "BlackElo") be = val($0)
  else if (key == "Result") r = val($0)
  else if (key == "Termination") t = val($0)
  else if (key == "TimeControl") tc = val($0)
  else if (key == "Date") dt = val($0)
  next
}
$0 != "" { sub(/\r$/, ""); mv = (mv == "" ? $0 : mv " " $0) }
END { flush() }
