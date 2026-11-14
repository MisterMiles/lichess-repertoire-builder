# Teilt einen PGN Strom (stdin) blockweise an N Ausgabedateien oder Fifos auf, immer an einer
# Partiegrenze. Jeder Worker bekommt nur sein Stück statt den ganzen Strom wie bei tee.
# Aufruf: zstd -dc monat.pgn.zst | python3 verteilen.py N OUT_0 ... OUT_N-1
import queue, sys, threading

n = int(sys.argv[1])
outs = [open(p, "wb") for p in sys.argv[2:2 + n]]
assert len(outs) == n, "Anzahl der Ausgaben passt nicht zu N"
# Ein Thread je Ausgabe, sonst blockiert das Schreiben an einen langsamen Worker alle anderen.
qs = [queue.Queue(maxsize=3) for _ in outs]


def pumpe(q, o):
    while (block := q.get()) is not None:
        o.write(block)
    o.close()


ts = [threading.Thread(target=pumpe, args=a) for a in zip(qs, outs)]
for t in ts:
    t.start()
buf, i = b"", 0
while d := sys.stdin.buffer.read(1 << 20):
    buf += d
    cut = buf.rfind(b"\n[Event ")
    if cut < 0:
        continue
    qs[i % n].put(buf[:cut + 1])
    buf = buf[cut + 1:]
    i += 1
qs[i % n].put(buf)
for q in qs:
    q.put(None)
for t in ts:
    t.join()
