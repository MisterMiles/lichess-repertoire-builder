# Wandelt eine PGN Datei in eine kompakte Tabelle (TSV) für repertoire.py.
# Aufruf: awk -v plies=30 -f pgn_tabelle.awk datei.pgn > datei.tsv
# Spalten: Site, White, Black, WhiteElo, BlackElo, Result, Termination,
#          TimeControl, Date, Halbzüge gesamt, letzter Zug, erste N Halbzüge
function val() { v = $0; sub(/^\[[A-Za-z]+ "/, "", v); sub(/"\]\r?$/, "", v); return v }
function flush() {
  if (mv == "") return
  s = mv; gsub(/\{[^}]*\}/, "", s); n = split(s, a, " "); k = 0; out = ""; last = ""
  for (i = 1; i <= n; i++) {
    x = a[i]
    if (x ~ /^[0-9]+\./ || x == "1-0" || x == "0-1" || x == "1/2-1/2" || x == "*") continue
    k++; last = x; if (k <= plies) out = out (k > 1 ? " " : "") x
  }
  print site "\t" w "\t" b "\t" we "\t" be "\t" r "\t" t "\t" tc "\t" dt "\t" k "\t" last "\t" out
  mv = ""; site = w = b = we = be = r = t = tc = dt = ""
}
BEGIN { if (plies == "") plies = 30 }
/^\[Event / { flush(); inm = 0 }
/^\[Site / { site = val() }
/^\[White / { w = val() }
/^\[Black / { b = val() }
/^\[WhiteElo / { we = val() }
/^\[BlackElo / { be = val() }
/^\[Result / { r = val() }
/^\[Termination / { t = val() }
/^\[TimeControl / { tc = val() }
/^\[Date / { dt = val() }
/^1\. / { inm = 1 }
inm && !/^\[/ { mv = mv " " $0 }
END { flush() }
