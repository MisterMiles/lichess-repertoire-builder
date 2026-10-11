"""Springer Animation für Wartezeiten.

Ein Springer hüpft im L über ein zweireihiges Brett, hinter ihm füllen sich die
Felder. Dazu Prozent und geschätzte Restzeit. Ohne Terminal (Ausgabe in eine
Datei umgeleitet) oder mit REPERTOIRE_PLAIN=1 bleibt alles schlicht.

Als Modul:   s = Springer("Stockfish"); s.zeichne(0.42, "noch ca. 3 Min."); s.fertig("fertig in 5 Min.")
Für Bash:    python3 animation.py "Download 2026-07" --groesse DATEI --gesamt BYTES [--start BYTES]
             python3 animation.py "Filtern 2026-07" --pv DATEI      (Ausgabe von pv -n)
             Läuft, bis es ein SIGTERM bekommt, und schreibt dann die Abschlusszeile.
"""
import os, shutil, signal, sys, time

FIGUREN = ("♞", "♘")
LEER, SPUR = "·", "▪"


def an():
    return (sys.stderr.isatty() and not os.environ.get("REPERTOIRE_PLAIN")
            and os.environ.get("TERM", "") != "dumb")


def dauer(sek):
    sek = int(sek)
    if sek >= 3600: return f"{sek // 3600} Std. {sek % 3600 // 60} Min."
    return f"{sek // 60} Min." if sek >= 60 else f"{sek} Sek."


def zahl(x, st=1):
    return f"{x:.{st}f}".replace(".", ",")


class Springer:
    def __init__(self, name):
        self.name, self.t0, self.tick, self.gezeichnet = name, time.time(), 0, False
        self.breite = shutil.get_terminal_size((80, 24)).columns
        self.spruenge = 12 if self.breite >= 100 else (8 if self.breite >= 70 else 4)   # Sprünge über das ganze Brett

    def _reihen(self, anteil):
        k = min(int(anteil * self.spruenge + 1e-9), self.spruenge)
        spalten = 2 * self.spruenge + 1
        sp, zeile = 2 * k, k % 2                            # Springerzug: zwei nach rechts, eine Reihe hoch oder runter
        figur = FIGUREN[self.tick % 2] if anteil < 1 else FIGUREN[0]
        reihen = []
        for r in (0, 1):
            reihen.append("".join(figur if (r == zeile and c == sp) else (SPUR if c < sp or (c == sp and r != zeile) else LEER)
                                  for c in range(spalten)))
        return reihen

    def zeichne(self, anteil, info="", info_oben=""):
        anteil = max(0.0, min(anteil, 1.0)); self.tick += 1
        r0, r1 = self._reihen(anteil)
        z1 = f"  {self.name:<16} {r0}  {zahl(anteil * 100):>5} %  {info_oben}".rstrip()[:self.breite - 1]
        z2 = f"  {'':<16} {r1}  {info}".rstrip()[:self.breite - 1]       # nie umbrechen, sonst verrutscht die Animation
        out = ("\x1b[1A\r" if self.gezeichnet else "") + "\x1b[2K" + z1 + "\n\x1b[2K" + z2
        sys.stderr.write(out); sys.stderr.flush(); self.gezeichnet = True

    def fertig(self, text=None):
        text = text or f"fertig in {dauer(time.time() - self.t0)}"
        r0, _ = self._reihen(1.0)
        vorn = "\x1b[1A\r" if self.gezeichnet else ""
        sys.stderr.write(f"{vorn}\x1b[2K" + f"  {self.name:<16} {r0}  {text}"[:self.breite - 1] + "\n\x1b[2K"); sys.stderr.flush()
        self.gezeichnet = False


class Restzeit:
    """Schätzt die Restzeit aus dem Fortschritt seit dem ersten Messpunkt."""
    def __init__(self):
        self.a0 = self.t0 = None

    def text(self, a):
        jetzt = time.time()
        if self.a0 is None: self.a0, self.t0 = a, jetzt
        if a - self.a0 < 0.005 or jetzt - self.t0 < 3: return "Restzeit wird geschätzt"
        return f"noch ca. {dauer((jetzt - self.t0) / (a - self.a0) * (1 - a))}"


def _lies_pv(pfad):
    try:
        with open(pfad, "rb") as f:
            f.seek(0, 2); n = f.tell(); f.seek(max(0, n - 64))
            zeilen = f.read().decode(errors="ignore").split()
        return float(zeilen[-1]) / 100 if zeilen else 0.0
    except (OSError, ValueError):
        return 0.0


def main():
    args = sys.argv[1:]
    if not args: print(__doc__); return
    name = args[0]; opt = dict(zip(args[1::2], args[2::2]))
    s = Springer(name); rz = Restzeit(); stopp = []
    signal.signal(signal.SIGTERM, lambda *_: stopp.append(1))
    signal.signal(signal.SIGINT, lambda *_: stopp.append(1))
    gesamt = float(opt.get("--gesamt", 0) or 0); start = float(opt.get("--start", 0) or 0)
    verlauf = []                                                  # (Zeit, Bytes) für die Geschwindigkeit
    while not stopp:
        if "--groesse" in opt:
            try: n = os.path.getsize(opt["--groesse"])
            except OSError: n = start
            jetzt = time.time(); verlauf.append((jetzt, n)); verlauf = [v for v in verlauf if jetzt - v[0] <= 10]
            mbs = (verlauf[-1][1] - verlauf[0][1]) / max(verlauf[-1][0] - verlauf[0][0], 1e-6) / 1e6
            a = n / gesamt if gesamt else 0.0
            oben = f"{zahl(n / 1e9)}/{zahl(gesamt / 1e9)} GB" if gesamt else f"{zahl(n / 1e9)} GB"
            info = f"{zahl(mbs)} MB/s  " + rz.text(a)
        else:
            a = _lies_pv(opt.get("--pv", "")); info = rz.text(a); oben = ""
        s.zeichne(a, info, oben)
        for _ in range(5):
            if stopp: break
            time.sleep(0.1)
    s.fertig()


if __name__ == "__main__":
    main()
