"""Lädt eine Datei mit mehreren gleichzeitigen Verbindungen (HTTP Range), weil database.lichess.org
jede einzelne Verbindung stark drosselt. Setzt abgebrochene Läufe fort.

Aufruf: python3 laden_parallel.py URL ZIEL GESAMT_BYTES VERBINDUNGEN
Die Datei wird in Blöcke zu 16 MiB geteilt und an den Blockgrenzen beschrieben. Welche Blöcke schon
komplett da sind, steht in ZIEL.blocks. Ohne diese Datei zählt ein vorhandenes ZIEL als lückenloser
Anfang (so sieht es nach einem einzelnen curl Download aus).
Exit 0 nur, wenn alles da ist, dann hat ZIEL genau GESAMT_BYTES.
"""
import os, subprocess, sys, threading, time

BLOCK = 16 << 20
url, ziel, gesamt, n = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
liste = ziel + ".blocks"
anzahl = -(-gesamt // BLOCK)

fertig = set()
if os.path.exists(liste):
    fertig = {int(x) for x in open(liste).read().split()}
elif os.path.exists(ziel):
    fertig = set(range(min(os.path.getsize(ziel), gesamt) // BLOCK))
offen = [i for i in range(anzahl) if i not in fertig]

fd = os.open(ziel, os.O_RDWR | os.O_CREAT)
notiz = open(liste, "w", buffering=1)
for i in sorted(fertig): notiz.write(f"{i}\n")      # legt die Datei auch beim ersten Mal an
sperre = threading.Lock(); fehler = []


def hole(i):
    a = i * BLOCK; e = min(a + BLOCK, gesamt) - 1
    for versuch in range(6):
        p = subprocess.Popen(["curl", "-sfL", "-r", f"{a}-{e}", url], stdout=subprocess.PIPE)
        pos = a
        while chunk := p.stdout.read(1 << 20):
            os.pwrite(fd, chunk, pos); pos += len(chunk)
        p.wait()
        if p.returncode == 0 and pos == e + 1: return True
        time.sleep(10 * (versuch + 1))
    return False


def arbeiter():
    while not fehler:
        with sperre:
            if not offen: return
            i = offen.pop(0)
        if hole(i):
            with sperre: notiz.write(f"{i}\n")
        else:
            fehler.append(i); return


ts = [threading.Thread(target=arbeiter, daemon=True) for _ in range(max(1, n))]
try:
    for t in ts: t.start()
    for t in ts: t.join()
except KeyboardInterrupt:
    os._exit(130)
if fehler or offen:
    sys.exit(1)
os.ftruncate(fd, gesamt); os.close(fd); notiz.close(); os.remove(liste)
