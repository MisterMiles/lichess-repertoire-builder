#!/usr/bin/env python3
"""Misst, wie viele Partien über andere Zugfolgen in die Stellungen eines Repertoires kommen.

Aufruf:  python3 zugumstellungen.py konfiguration.json andere.tsv

andere.tsv entsteht mit lichess_filter.sh, z. B. alle Partien, in denen der
eigene Schlüsselzug erst später kommt:
  bash lichess_filter.sh --enthaelt d4 --bis-zug 4 --nicht-start "1. d4" -i monat.pgn.zst -o andere.pgn --tsv andere.tsv

Gezählt werden die Stellungen, die im Repertoire vorkommen (gleiche Regeln
wie repertoire.py), also nur Züge, die man selbst auch spielt.
"""
import sys, collections, chess
sys.path.insert(0, __import__("os").path.dirname(__file__))
from repertoire import lade_config, lade_partien, lade_repertoire, Baum, Fortschritt, zugfolge, zahl

def main():
    if len(sys.argv) < 3: print(__doc__); sys.exit(1)
    cfg = lade_config(sys.argv[1]); cfg["strukturen_zug"] = 99
    daten = lade_partien(cfg)
    rep = lade_repertoire(cfg)
    b = chess.Board()
    for m in cfg["start_san"]: b.push_san(m)
    L = len(cfg["start_san"]); erste = L if b.turn != cfg["ich"] else L + 1
    baum = Baum(cfg, daten, rep); baum.seen[b.epd()] = list(cfg["start_san"])
    baum.daten(b, list(cfg["start_san"]), erste)
    ziel = set(baum.knoten_von)
    print(f"  {len(ziel)} Stellungen im Repertoire", flush=True)
    zeilen = sum(1 for _ in open(sys.argv[2], encoding="utf-8"))
    fs = Fortschritt("Andere Partien", zeilen)
    treffer = 0; gesamt = 0; folgen = collections.Counter()
    maxp = cfg["bis_zug"] * 2
    for zeile in open(sys.argv[2], encoding="utf-8"):
        fs.schritt()
        f = zeile.rstrip("\n").split("\t")
        if len(f) < 12: continue
        gesamt += 1
        b = chess.Board(); zuege = []
        for z in f[11].split()[:maxp]:
            try: b.push_san(z.rstrip("?!"))
            except ValueError: break
            zuege.append(z.rstrip("?!"))
            if b.epd() in ziel:
                treffer += 1; folgen[" ".join(zuege)] += 1
                break
    fs.fertig()
    eigen = daten["n_pool"]
    print(f"\nAndere Zugfolgen: {gesamt} Partien geprüft, {treffer} erreichen eine Stellung des Repertoires.")
    if eigen: print(f"Das sind {zahl(100 * treffer / eigen)} % zusätzlich zu den {eigen} ausgewerteten eigenen Partien.")
    print("\nHäufigste Zugfolgen bis zum Eintritt:")
    for z, n in folgen.most_common(15):
        print(f"  {n:6d}  {zugfolge(z.split(), cfg)}")

if __name__ == "__main__":
    main()
