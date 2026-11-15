"""Liest Startzüge aus einer Textdatei, einem PGN Ausschnitt oder einem Lichess Link.

    python3 startzuege.py QUELLE [N]     druckt die Züge ohne Zugnummern, z. B. "e4 c5 Nf3 e6"

QUELLE ist eine Datei oder ein Link von lichess.org (Partie oder Studienkapitel).
N begrenzt auf die ersten N vollen Züge. Tags, Kommentare, Varianten und Bewertungen
werden ignoriert, bei mehreren Partien zählt die erste.
"""
import re, sys, urllib.parse, urllib.request


def lichess_url(link):
    u = urllib.parse.urlparse(link)
    if u.hostname not in ("lichess.org", "www.lichess.org"):
        sys.exit("Nur Links von lichess.org werden unterstützt.")
    teile = [t for t in u.path.split("/") if t]
    if len(teile) >= 3 and teile[0] == "study":
        return f"https://lichess.org/api/study/{teile[1]}/{teile[2]}.pgn?clocks=false&comments=false"
    if len(teile) >= 1 and re.fullmatch(r"[A-Za-z0-9]{8,12}", teile[0]):
        return f"https://lichess.org/game/export/{teile[0][:8]}?clocks=false&evals=false&opening=false"
    sys.exit("Link nicht erkannt. Erwartet wird eine Partie (lichess.org/ID) oder ein Studienkapitel (lichess.org/study/ID/ID).")


def lade(quelle):
    if quelle.startswith("http"):
        req = urllib.request.Request(lichess_url(quelle), headers={"User-Agent": "repertoire-builder", "Accept": "application/x-chess-pgn"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r: return r.read().decode("utf-8", "ignore")
        except OSError as e:
            sys.exit(f"Link konnte nicht geladen werden: {e}")
    try:
        return open(quelle, encoding="utf-8").read()
    except OSError as e:
        sys.exit(f"Datei nicht lesbar: {e}")


def zuege(text, n=None):
    text = [p for p in re.split(r"(?m)^(?=\[Event )", text) if p.strip()][0] if text.strip() else ""   # nur die erste Partie
    text = re.sub(r"^\[.*\]\s*$", " ", text, flags=re.M)                 # Tags
    text = re.sub(r";[^\n]*", " ", text)                                 # Zeilenkommentare
    text = re.sub(r"\{[^}]*\}", " ", text)                               # Kommentare
    while True:                                                          # Varianten, auch verschachtelt
        neu = re.sub(r"\([^()]*\)", " ", text)
        if neu == text: break
        text = neu
    out = []
    for t in text.split():
        t = re.sub(r"^\d+\.+", "", t)
        t = re.sub(r"[!?]+$", "", t)
        if not t or t.startswith("$") or t in ("1-0", "0-1", "1/2-1/2", "*"): continue
        out.append(t)
    return out[:2 * n] if n else out


if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    n = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None
    z = zuege(lade(sys.argv[1]), n)
    if not z: sys.exit("Keine Züge gefunden.")
    print(" ".join(z))
