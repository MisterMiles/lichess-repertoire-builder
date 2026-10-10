#!/usr/bin/env python3
"""Baut aus Lichess Partien (Tabelle von lichess_filter.sh) ein kommentiertes
Eröffnungsrepertoire als PGN, für Weiß oder Schwarz.

Aufruf:   python3 repertoire.py konfiguration.json
Benötigt: pip install chess   und Stockfish (z. B. brew install stockfish)

Ablauf: Partien laden, nach Startzügen und Systemregel filtern, Zugbaum nach
Stellung zählen, Kapitel bilden, Linienenden mit Stockfish bewerten,
Musterpartien suchen, PGN schreiben. Stockfish Ergebnisse werden in einer
Cache Datei neben der Ausgabe gespeichert, ein Abbruch kostet daher nichts.
"""
import sys, os, json, re, math, collections, datetime
from multiprocessing import Pool
import chess, chess.pgn, chess.engine

STANDARD = {
    "farbe": "weiss", "erste_antworten": 10, "antworten": 3, "fruehe_zuege_ab_5_prozent": [2, 3],
    "min_partien": 20, "bis_zug": 15, "hv_tiefe": 4, "kapitel_max": 800, "kapitel_teilen_ab": 300,
    "zusammenfassung_bis_zug": 5, "system": [], "ohne_systemfilter": [], "repertoire_pgn": None,
    "repertoire_kommentare": True, "kommentare_entfernen": [], "anhang_pgn": [], "statistik": False,
    "stockfish": "stockfish", "tiefe": 18, "prozesse": 2, "eco": "?", "notation": "de",
}

# ---------------------------------------------------------------- Hilfen
def lade_config(pfad):
    cfg = dict(STANDARD); cfg.update(json.load(open(pfad, encoding="utf-8")))
    basis = os.path.dirname(os.path.abspath(pfad))
    for k in ("daten", "ausgabe", "repertoire_pgn"):
        if cfg.get(k) and not os.path.isabs(cfg[k]): cfg[k] = os.path.join(basis, cfg[k])
    cfg["anhang_pgn"] = [p if os.path.isabs(p) else os.path.join(basis, p) for p in cfg["anhang_pgn"]]
    cfg["ich"] = chess.WHITE if cfg["farbe"].lower().startswith("w") else chess.BLACK
    cfg["start_san"] = [t for t in re.sub(r"\d+\.(\.\.)?", " ", cfg["start"]).split() if t]
    return cfg

def epd(b): return b.epd()
def key(fen): return " ".join(fen.split()[:4])

def de(s, cfg):
    return s.translate(str.maketrans("NBRQK", "SLTDK")) if cfg["notation"] == "de" else s

def label(b, san, cfg):
    return f"{b.fullmove_number}.{de(san, cfg)}" if b.turn == chess.WHITE else f"{b.fullmove_number}...{de(san, cfg)}"

def pfad_text(pfad, cfg):
    b = chess.Board(); ms = []
    for m in pfad: mv = b.parse_san(m); ms.append(mv); b.push(mv)
    return de(chess.Board().variation_san(ms), cfg)

def winkel(cp):
    e = cp / 100
    if abs(e) < 0.3: return 11
    if e >= 1.5: return 18
    if e >= 0.7: return 16
    if e > 0: return 14
    if e <= -1.5: return 19
    if e <= -0.7: return 17
    return 15

# ---------------------------------------------------------------- Daten
def lade_partien(cfg):
    start = cfg["start_san"]; L = len(start); maxp = cfg["bis_zug"] * 2
    ich = cfg["ich"]; regeln = cfg["system"]; ohne = set(cfg["ohne_systemfilter"])
    zaehler = collections.defaultdict(collections.Counter)
    alle = []; n_sys = 0; n_ges = 0
    for zeile in open(cfg["daten"], encoding="utf-8"):
        f = zeile.rstrip("\n").split("\t")
        if len(f) < 12 or f[5] not in ("1-0", "0-1", "1/2-1/2"): continue
        zuege = [t.rstrip("?!") for t in f[11].split()]
        if zuege[:L] != start: continue
        n_ges += 1
        alle.append(f)
        # Systemregel: jeder Eintrag muss erfüllt sein
        ok = True
        for r in regeln:
            treffer = False
            for i, z in enumerate(zuege):
                if (i % 2 == 0) != (ich == chess.WHITE): continue
                if i // 2 + 1 > r.get("spaetestens_zug", 99): break
                if z == r["zug"]:
                    vorher = [zuege[j] for j in range(i % 2, i, 2)]
                    treffer = not any(v in vorher for v in r.get("nicht_vorher", []))
                    break
            ok = ok and treffer
        erste = next((zuege[i] for i in range(L, len(zuege)) if (i % 2 == 0) != (ich == chess.WHITE)), None)
        if not ok and erste not in ohne: continue
        if ok: n_sys += 1
        b = chess.Board()
        for p, z in enumerate(zuege[:maxp]):
            try: mv = b.parse_san(z)
            except ValueError: break
            if p >= L: zaehler[(p, epd(b))][b.san(mv)] += 1
            b.push(mv)
    print(f"Partien mit Startzügen: {n_ges}, davon mit Systemregel: {n_sys}", flush=True)
    return zaehler, alle, n_ges, n_sys

def lade_repertoire(cfg):
    """Alle Stellungen aus der Repertoire PGN: Züge je Stellung, eigene Züge gelten als Repertoirezüge."""
    rep = {}
    if not cfg.get("repertoire_pgn"): return rep
    weg = [re.compile(x) for x in cfg["kommentare_entfernen"]]
    def filt(c):
        if not cfg["repertoire_kommentare"]: return ""
        teile = re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ(\[])", c.strip())
        return " ".join(t for t in teile if t and not any(w.search(t) for w in weg))
    h = open(cfg["repertoire_pgn"], encoding="utf-8-sig")
    while True:
        g = chess.pgn.read_game(h)
        if g is None: break
        if "FEN" in g.headers: continue
        st = [g]
        while st:
            x = st.pop(); b = x.board(); k = epd(b)
            for v in x.variations:
                d = rep.setdefault(k, {}).setdefault(v.move.uci(), {"san": b.san(v.move), "c": ""})
                c = filt(v.comment)
                if c and c not in d["c"]: d["c"] = (d["c"] + " " + c).strip()
                st.append(v)
    print(f"Repertoire PGN: {len(rep)} Stellungen", flush=True)
    return rep

# ---------------------------------------------------------------- Zugbaum
class Baum:
    def __init__(self, cfg, zaehler, rep):
        self.cfg, self.z, self.rep = cfg, zaehler, rep
        self.maxp = cfg["bis_zug"] * 2; self.seen = {}

    def knoten(self, b, san, art, **kw):
        mv = b.parse_san(san); b2 = b.copy(); b2.push(mv)
        r = self.rep.get(epd(b), {}).get(mv.uci())
        d = {"san": san, "uci": mv.uci(), "fb": b.fen(), "fa": b2.fen(), "art": art, "rep": False,
             "c": r["c"] if r else "", "kids": [], "transpo": None}
        d.update(kw); return d, b2

    def nur_rep(self, b, ply, lokal):
        out = []
        if ply >= self.maxp + 6: return out
        for u, r in self.rep.get(epd(b), {}).items():
            mv = chess.Move.from_uci(u); b2 = b.copy(); b2.push(mv)
            if epd(b2) in lokal: continue
            d, _ = self.knoten(b, r["san"], "rep")
            d["kids"] = self.nur_rep(b2, ply + 1, lokal | {epd(b2)})
            out.append(d)
        return out

    def daten(self, b, ply, pfad, erste_ply):
        cfg = self.cfg; k = epd(b)
        c = self.z.get((ply, k)); tot = sum(c.values()) if c else 0
        repz = self.rep.get(k, {})
        picks = []
        if ply < self.maxp and tot >= cfg["min_partien"]:
            rang = c.most_common()
            if b.turn == cfg["ich"]:
                eigene = [r["san"] for r in repz.values()]
                picks = [rang[0][0]] + [s for s in eigene if s != rang[0][0] and c.get(s, 0) > 0]
            elif ply == erste_ply:
                ohne = set(cfg["ohne_systemfilter"])
                picks = [m for m, _ in rang if m not in ohne][:cfg["erste_antworten"]]
                picks += [m for m in cfg["ohne_systemfilter"] if m in c]
            elif b.fullmove_number in cfg["fruehe_zuege_ab_5_prozent"]:
                picks = [m for i, (m, x) in enumerate(rang) if i < cfg["antworten"] or x / tot >= 0.05]
            else:
                picks = [m for m, _ in rang[:cfg["antworten"]]]
        out = []
        for i, m in enumerate(picks):
            d, b2 = self.knoten(b, m, "daten", cnt=c[m], anteil=round(100 * c[m] / tot, 1),
                                rep=(b.turn == cfg["ich"] and i > 0))
            d2 = self.z.get((ply + 1, epd(b2))); d["n"] = sum(d2.values()) if d2 else c[m]
            if epd(b2) in self.seen: d["transpo"] = self.seen[epd(b2)]
            else:
                self.seen[epd(b2)] = pfad + [m]
                d["kids"] = self.daten(b2, ply + 1, pfad + [m], erste_ply)
            out.append(d)
        if ply < self.maxp:
            for u, r in repz.items():
                if r["san"] in picks: continue
                mv = chess.Move.from_uci(u); b2 = b.copy(); b2.push(mv)
                d, _ = self.knoten(b, r["san"], "rep", rep=(b.turn == cfg["ich"] and bool(picks)))
                if epd(b2) in self.seen: d["transpo"] = self.seen[epd(b2)]
                else: d["kids"] = self.nur_rep(b2, ply + 1, {epd(b), epd(b2)})
                out.append(d)
        return out

def groesse(d): return 1 + sum(groesse(k) for k in d["kids"])

# ---------------------------------------------------------------- Kapitel
def kapitel_bilden(cfg, wurzel_kids):
    start = cfg["start_san"]; ich = cfg["ich"]
    hv = []   # (pfad_davor, kids, brett)
    kids = wurzel_kids; pfad = list(start); b = chess.Board()
    for m in start: b.push_san(m)
    while kids:
        hv.append((list(pfad), kids, b.copy()))
        k0 = kids[0]
        if k0["art"] != "daten" or k0["transpo"]: break
        pfad.append(k0["san"]); b.push_san(k0["san"]); kids = k0["kids"]
    gegner = [i for i, (_, _, bb) in enumerate(hv) if bb.turn != ich]
    if not gegner: return [{"teil": 1, "name": "Hauptvariante", "pfad": start, "eintraege": wurzel_kids}]
    s = next((i for i in gegner if hv[i][2].fullmove_number >= cfg["hv_tiefe"]), gegner[-1])
    kap = []; teil = 1
    p, ks, bb = hv[s]
    for k in ks:
        if k["art"] == "daten" and not k["transpo"]:
            kap.append({"teil": teil, "name": f"HV mit {label(bb, k['san'], cfg)}", "pfad": p, "eintraege": [k]})
    rest = [k for k in ks if k["art"] != "daten"]
    if rest: kap.append({"teil": teil, "name": f"HV Diverse {bb.fullmove_number}. Züge", "pfad": p, "eintraege": rest})
    for i in range(s - 1, -1, -1):
        p, ks, bb = hv[i]
        neben = [k for k in ks[1:] if k["art"] == "daten" and not k["transpo"]]
        rest = [k for k in ks[1:] if k["art"] != "daten"]
        if not neben and not rest: continue
        teil += 1
        for k in neben:
            kap += teilen(cfg, p, k, bb, teil)
        if rest:
            wer = "eigene" if bb.turn == ich else ""
            kap.append({"teil": teil, "name": f"Diverse {wer} {bb.fullmove_number}. Züge".replace("  ", " "), "pfad": p, "eintraege": rest})
    return kap

def teilen(cfg, p, k, bb, teil):
    name = label(bb, k["san"], cfg)
    if groesse(k) <= cfg["kapitel_max"] or not k["kids"] or k["kids"][0]["art"] != "daten":
        return [{"teil": teil, "name": name, "pfad": p, "eintraege": [k]}]
    w = k["kids"][0]; b2 = bb.copy(); b2.push_san(k["san"]); b3 = b2.copy(); b3.push_san(w["san"])
    gross = [c for c in w["kids"] if groesse(c) > cfg["kapitel_teilen_ab"] and c["art"] == "daten"]
    if not gross: return [{"teil": teil, "name": name, "pfad": p, "eintraege": [k]}]
    wp = p + [k["san"], w["san"]]; out = []
    for c in gross:
        out.append({"teil": teil, "name": f"{name} {label(b2, w['san'], cfg)} {de(c['san'], cfg)}", "pfad": wp, "eintraege": [c]})
    rest = [c for c in w["kids"] if c not in gross]
    if rest: out.append({"teil": teil, "name": f"{name} {label(b2, w['san'], cfg)} Diverse", "pfad": wp, "eintraege": rest})
    if len(k["kids"]) > 1:
        out.append({"teil": teil, "name": f"{name} weitere {b2.fullmove_number}. Züge", "pfad": p + [k["san"]], "eintraege": k["kids"][1:]})
    return out

# ---------------------------------------------------------------- Stockfish
_eng = None
def _init(pfad):
    global _eng
    _eng = chess.engine.SimpleEngine.popen_uci(pfad); _eng.configure({"Threads": 1, "Hash": 64})
def _bewerte(args):
    fen, tiefe = args; b = chess.Board(fen)
    if b.is_game_over():
        o = b.outcome(); return fen, {"s": 0 if o.winner is None else (10000 if o.winner else -10000), "m": None}
    info = _eng.analyse(b, chess.engine.Limit(depth=tiefe))
    return fen, {"s": info["score"].white().score(mate_score=10000), "m": info["pv"][0].uci() if info.get("pv") else None}

def stockfish(cfg, fens):
    cache_pfad = os.path.splitext(cfg["ausgabe"])[0] + "_stockfish.json"
    cache = json.load(open(cache_pfad)) if os.path.exists(cache_pfad) else {}
    offen = sorted({f for f in fens if key(f) not in cache})
    print(f"Stockfish: {len(fens)} Endstellungen, davon neu zu rechnen: {len(offen)}", flush=True)
    if offen:
        with Pool(cfg["prozesse"], initializer=_init, initargs=(cfg["stockfish"],)) as pool:
            for i, (f, r) in enumerate(pool.imap_unordered(_bewerte, [(f, cfg["tiefe"]) for f in offen], chunksize=4), 1):
                cache[key(f)] = r
                if i % 100 == 0:
                    print(f"  {i} von {len(offen)}", flush=True); json.dump(cache, open(cache_pfad, "w"))
        json.dump(cache, open(cache_pfad, "w"))
    return cache

# ---------------------------------------------------------------- Musterpartien
def musterpartien(cfg, alle, ziele):
    best = {}; maxp = cfg["bis_zug"] * 2
    for f in alle:
        try: schnitt = (int(f[3]) + int(f[4])) / 2
        except ValueError: continue
        b = chess.Board()
        for z in f[11].split()[:maxp]:
            try: b.push_san(z.rstrip("?!"))
            except ValueError: break
            k = epd(b)
            if k in ziele and (k not in best or schnitt > best[k][0]):
                d = f[8]; ort = f[0].replace("https://", "")
                best[k] = (schnitt, f"{f[5]} ({(int(f[9]) + 1) // 2}) {f[1]} ({f[3]}) gegen {f[2]} ({f[4]}), Lichess {d[5:7]}.{d[:4]}, {ort}")
    print(f"Musterpartien: {len(best)} von {len(ziele)} Endstellungen", flush=True)
    return {k: v[1] for k, v in best.items()}

# ---------------------------------------------------------------- PGN
def blaetter(d, out):
    if not d["kids"] and not d["transpo"]: out.add(d["fa"])
    for k in d["kids"]: blaetter(k, out)

def schreiben(cfg, kapitel, intro_pfad, zusammenfassung, anhang, sf, muster, info):
    heute = datetime.date.today().strftime("%Y.%m.%d")
    praefixe = []
    for i, c in enumerate(kapitel, 2):
        for e in c["eintraege"]: praefixe.append((c["pfad"] + [e["san"]], i))
    def verweis(p):
        best = None
        for pre, i in praefixe:
            if len(pre) <= len(p) and p[:len(pre)] == pre and (best is None or len(pre) > len(best[0])): best = (pre, i)
        return (f"Zugumstellung, siehe Kapitel {best[1]:02d} nach {pfad_text(p, cfg)}." if best
                else f"Zugumstellung zur Stellung nach {pfad_text(p, cfg)}.")
    def ende(node, fen, mit_partie=True):
        teile = []; r = sf.get(key(fen))
        if r and r["s"] is not None:
            node.nags.add(winkel(r["s"]))
            if r["m"]:
                m = chess.Move.from_uci(r["m"])
                teile.append(f"[%cal G{chess.square_name(m.from_square)}{chess.square_name(m.to_square)}]")
        if mit_partie and key(fen) in muster: teile.append(muster[key(fen)])
        return teile
    def add(gn, d, mit_partie=True):
        ch = gn.add_variation(chess.Move.from_uci(d["uci"])); teile = []
        if d.get("rep"): teile.append("Repertoirezug")
        if cfg["statistik"] and d["art"] == "daten":
            teile.append(f"{str(d['anteil']).replace('.', ',')} %, {d['cnt']} Partien")
        if d["c"]: teile.append(d["c"])
        if d["transpo"]: teile.append(verweis(d["transpo"]))
        elif not d["kids"]: teile += ende(ch, d["fa"], mit_partie)
        ch.comment = " ".join(teile)
        for k in d["kids"]: add(ch, k, mit_partie)
    def spiel(titel):
        g = chess.pgn.Game(); g.headers.clear()
        for k, v in (("Event", "?"), ("Site", "?"), ("Date", heute), ("Round", "?"), ("White", titel), ("Black", "?"),
                     ("Result", "*"), ("ECO", cfg["eco"]), ("Annotator", "repertoire.py (Lichess, Stockfish)"),
                     ("PlyCount", "0"), ("SourceTitle", cfg["titel"]), ("SourceVersionDate", heute)):
            g.headers[k] = v
        return g
    def zuege(g, pfad):
        b = chess.Board(); n = g
        for m in pfad: mv = b.parse_san(m); b.push(mv); n = n.add_variation(mv)
        return n, b
    spiele = []
    # Intro
    g = spiel("01 Intro"); g.comment = info
    n, b = zuege(g, intro_pfad); n.comment = " ".join(ende(n, b.fen()))
    spiele.append(g)
    for i, c in enumerate(kapitel, 2):
        g = spiel(f"Teil {c['teil']}: {i:02d} {c['name']}")
        n, _ = zuege(g, c["pfad"])
        for e in c["eintraege"]: add(n, e)
        spiele.append(g)
    nr = len(kapitel) + 2; teil = (kapitel[-1]["teil"] + 1) if kapitel else 1
    for titel, g0 in anhang:
        g = spiel(f"Teil {teil}: {nr:02d} {titel}"); g.comment = g0.comment
        def kopie(src, dst):
            for v in src.variations:
                x = dst.add_variation(v.move); x.comment = v.comment; x.nags = set(v.nags); kopie(v, x)
        kopie(g0, g); spiele.append(g); nr += 1
    g = spiel(f"{nr:02d} Zusammenfassung")
    n, _ = zuege(g, cfg["start_san"])
    for e in zusammenfassung: add(n, e, mit_partie=False)
    spiele.append(g)
    with open(cfg["ausgabe"], "w", encoding="utf-8", newline="\r\n") as f:
        for g in spiele:
            g.headers["PlyCount"] = str(len(list(g.mainline_moves())))
            print(g, file=f, end="\n\n")
    print(f"Geschrieben: {cfg['ausgabe']} ({len(spiele)} Kapitel)", flush=True)

def kurz(d, ply, bis):
    """Kopie des Datenbaums bis zu einem Halbzug, ohne reine Repertoirelinien, für die Zusammenfassung."""
    e = dict(d); e["c"] = ""
    e["kids"] = [kurz(k, ply + 1, bis) for k in d["kids"] if k["art"] == "daten"] if ply + 1 < bis else []
    if ply + 1 >= bis: e["transpo"] = None
    return e

# ---------------------------------------------------------------- Hauptprogramm
def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    cfg = lade_config(sys.argv[1])
    zaehler, alle, n_ges, n_sys = lade_partien(cfg)
    rep = lade_repertoire(cfg)
    b = chess.Board()
    for m in cfg["start_san"]: b.push_san(m)
    L = len(cfg["start_san"]); erste = L if b.turn != cfg["ich"] else L + 1
    baum = Baum(cfg, zaehler, rep); baum.seen[epd(b)] = list(cfg["start_san"])
    wurzel = baum.daten(b, L, list(cfg["start_san"]), erste)
    kapitel = kapitel_bilden(cfg, wurzel)
    # Intro Linie: Hauptvariante bis zum Ende
    intro = list(cfg["start_san"]); kids = wurzel
    while kids and kids[0]["art"] == "daten" and not kids[0]["transpo"]:
        intro.append(kids[0]["san"]); kids = kids[0]["kids"]
    bis = cfg["zusammenfassung_bis_zug"] * 2 - L
    zus = [kurz(k, 0, bis) for k in wurzel if k["art"] == "daten"]
    anhang = []
    for p in cfg["anhang_pgn"]:
        h = open(p, encoding="utf-8-sig")
        while True:
            g = chess.pgn.read_game(h)
            if g is None: break
            anhang.append((g.headers.get("White", "?") if g.headers.get("Black", "?") == "?" else g.headers.get("Black"), g))
    fens = set()
    for c in kapitel:
        for e in c["eintraege"]: blaetter(e, fens)
    for e in zus: blaetter(e, fens)
    bb = chess.Board()
    for m in intro: bb.push_san(m)
    fens.add(bb.fen())
    sf = stockfish(cfg, fens)
    muster = musterpartien(cfg, alle, {key(f) for f in fens})
    seite = "Weiß" if cfg["ich"] == chess.WHITE else "Schwarz"
    info = (f"{cfg['titel']}. Repertoire für {seite}, Startzüge {de(cfg['start'], cfg)}. "
            f"Daten: {n_ges} Lichess Partien, davon {n_sys} mit der Systemregel. "
            f"REGELN: Bei jedem Zug des Gegners die {cfg['antworten']} meistgespielten Antworten, in den Zügen "
            f"{', '.join(map(str, cfg['fruehe_zuege_ab_5_prozent']))} zusätzlich jede ab 5 %. Bei {seite} ist der meistgespielte Zug Hauptvariante, "
            f"der Repertoirezug steht markiert daneben. Eine Linie verzweigt, solange mindestens {cfg['min_partien']} Partien die Stellung erreichen, "
            f"höchstens bis Zug {cfg['bis_zug']}. Zugumstellungen verweisen auf das Kapitel, in dem die Stellung zuerst vorkommt. "
            f"AM LINIENENDE: Bewertung von Stockfish (Tiefe {cfg['tiefe']}, aus Sicht von Weiß): = ausgeglichen, ⩲ oder ⩱ leichter Vorteil, "
            f"± oder ∓ klarer Vorteil, +- oder -+ entscheidender Vorteil. Grüner Pfeil = bester Zug. "
            f"Musterpartie = Lichess Partie mit dem höchsten Elo Schnitt, die die Stellung erreicht hat.")
    schreiben(cfg, kapitel, intro, zus, anhang, sf, muster, info)

if __name__ == "__main__":
    main()
