#!/usr/bin/env python3
"""Baut aus Lichess Partien (Tabelle von lichess_filter.sh) ein kommentiertes
Eröffnungsrepertoire als PGN, für Weiß oder Schwarz.

Aufruf:   python3 repertoire.py konfiguration.json
Benötigt: pip install chess   und Stockfish (z. B. brew install stockfish)

Ausgaben:
  <ausgabe>.pgn               Repertoire mit Hauptteil, Bauernstrukturen, Anhang, Zusammenfassung
  <ausgabe>_quickstart.pgn    die wahrscheinlichsten Linien zum schnellen Üben
  <ausgabe>_strukturen.json   Strukturen mit Zahlen, Grundlage für eigene Erklärungstexte
  <ausgabe>_stockfish.json    Zwischenspeicher der Engine, ein zweiter Lauf rechnet nur Neues
"""
import sys, os, json, re, math, time, collections, datetime
from multiprocessing import Pool
import chess, chess.pgn, chess.engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strukturen as strukturmodul

STANDARD = {
    "farbe": "weiss", "erste_antworten": 10, "antworten": 3, "fruehe_zuege_ab_5_prozent": [2, 3],
    "min_partien": 20, "bis_zug": 15, "hv_tiefe": 4, "kapitel_max": 800, "kapitel_teilen_ab": 300,
    "zusammenfassung_bis_zug": 5, "system": [], "ohne_systemfilter": [], "repertoire_pgn": None,
    "repertoire_kommentare": True, "repertoire_zuege": "alle", "kommentare_entfernen": [], "anhang_pgn": [], "statistik": False,
    "stockfish": "stockfish", "tiefe": 18, "prozesse": 2, "eco": "?", "notation": "de",
    "quickstart_linien": 15, "quickstart_bis_zug": 14,
    "fehler": True, "fehler_tiefe": 14, "fehler_grenze": 0.2, "fehler_min_anteil": 5,
    "fehler_min_partien": 10, "fehler_anzahl": 5,
    "strukturen_zug": 12, "strukturen_anzahl": 5, "strukturen_text": None,
    "plan_zuege": 5, "plan_min_partien": 5,
    "kapitel_min_anteil": 2, "kapitel_min_zug": 12, "verlaengern_min_partien": 5,
}

# ---------------------------------------------------------------- Hilfen
def lade_config(pfad):
    cfg = dict(STANDARD); cfg.update(json.load(open(pfad, encoding="utf-8")))
    basis = os.path.dirname(os.path.abspath(pfad))
    for k in ("daten", "ausgabe", "repertoire_pgn", "strukturen_text"):
        if cfg.get(k) and not os.path.isabs(cfg[k]): cfg[k] = os.path.join(basis, cfg[k])
    cfg["anhang_pgn"] = [p if os.path.isabs(p) else os.path.join(basis, p) for p in cfg["anhang_pgn"]]
    cfg["ich"] = chess.WHITE if cfg["farbe"].lower().startswith("w") else chess.BLACK
    cfg["start_san"] = [t for t in re.sub(r"\d+\.(\.\.)?", " ", cfg["start"]).split() if t]
    cfg["basis"] = os.path.splitext(cfg["ausgabe"])[0]
    if os.environ.get("REPERTOIRE_SCHNELL"):
        cfg["tiefe"] = min(cfg["tiefe"], 10); cfg["fehler_tiefe"] = min(cfg["fehler_tiefe"], 8)
        print("Schneller Probelauf: Stockfish Tiefe 10, Fehlersuche Tiefe 8", flush=True)
    return cfg

def epd(b): return b.epd()
def key(fen): return " ".join(fen.split()[:4])
def de(s, cfg): return s.translate(str.maketrans("NBRQ", "SLTD")) if cfg["notation"] == "de" else s
def zahl(x, st=1): return f"{x:.{st}f}".replace(".", ",")
def ev(cp): return ("+" if cp > 0 else "") + zahl(cp / 100, 2)
def wc(cp): return 2 / (1 + math.exp(-0.00368208 * max(-10000, min(10000, cp)))) - 1
def seite(farbe): return "Weiß" if farbe == chess.WHITE else "Schwarz"

def label(b, san, cfg):
    return f"{b.fullmove_number}.{de(san, cfg)}" if b.turn == chess.WHITE else f"{b.fullmove_number}...{de(san, cfg)}"

def zugfolge(pfad, cfg, ab=0):
    """Züge eines Pfads als Text, ab einem Halbzug, mit richtigen Zugnummern."""
    b = chess.Board()
    for m in pfad[:ab]: b.push_san(m)
    ms = []
    for m in pfad[ab:]: mv = b.parse_san(m); ms.append(mv); b.push(mv)
    b0 = chess.Board()
    for m in pfad[:ab]: b0.push_san(m)
    return de(b0.variation_san(ms), cfg) if ms else ""

def dauer(sek):
    sek = int(sek)
    return f"{sek // 3600} Std. {sek % 3600 // 60} Min." if sek >= 3600 else (f"{sek // 60} Min." if sek >= 60 else f"{sek} Sek.")

class Fortschritt:
    """Balken mit Prozent, Anzahl und geschätzter Restzeit."""
    def __init__(self, name, gesamt):
        self.name, self.gesamt, self.t0, self.n, self.zuletzt = name, max(gesamt, 1), time.time(), 0, 0.0
        self.zeige(True)
    def schritt(self, k=1):
        self.n += k; self.zeige(False)
    def zeige(self, sofort):
        jetzt = time.time()
        if not sofort and jetzt - self.zuletzt < 0.5: return
        self.zuletzt = jetzt; a = min(self.n / self.gesamt, 1.0); voll = int(a * 20)
        rest = f"noch ca. {dauer((jetzt - self.t0) / a * (1 - a))}" if a > 0.01 else "Restzeit wird geschätzt"
        sys.stderr.write(f"\r  {self.name:<13} [{'█' * voll}{'░' * (20 - voll)}] {zahl(a * 100):>5} %  {self.n}/{self.gesamt}  {rest}      ")
        sys.stderr.flush()
    def fertig(self):
        sys.stderr.write(f"\r  {self.name:<13} [{'█' * 20}] 100,0 %  fertig in {dauer(time.time() - self.t0)}{' ' * 30}\n")
        sys.stderr.flush()

# ---------------------------------------------------------------- Daten
def lade_partien(cfg):
    start = cfg["start_san"]; L = len(start); maxp = cfg["bis_zug"] * 2
    ich = cfg["ich"]; regeln = cfg["system"]; ohne = set(cfg["ohne_systemfilter"])
    S = cfg["strukturen_zug"] * 2
    zaehler = collections.defaultdict(collections.Counter)
    punkte = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0]))
    erreicht = collections.Counter()
    strukturen = []
    alle = []; n_sys = n_ges = n_pool = 0
    zeilen = sum(1 for _ in open(cfg["daten"], encoding="utf-8"))
    fs = Fortschritt("Partien laden", zeilen)
    for zeile in open(cfg["daten"], encoding="utf-8"):
        fs.schritt()
        f = zeile.rstrip("\n").split("\t")
        if len(f) < 12 or f[5] not in ("1-0", "0-1", "1/2-1/2"): continue
        zuege = [t.rstrip("?!") for t in f[11].split()]
        if zuege[:L] != start: continue
        n_ges += 1; alle.append(f)
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
        n_sys += ok; n_pool += 1
        pkt = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}[f[5]]
        if ich == chess.BLACK: pkt = 1 - pkt
        b = chess.Board(); struktur = None; hebel = set()
        for p, z in enumerate(zuege[:max(maxp, S + 6)]):
            k = epd(b) if L <= p <= maxp else None
            if k: erreicht[(p, k)] += 1
            if p == S: struktur = strukturdaten(b, ich)
            try: mv = b.parse_san(z)
            except ValueError: break
            if k and p < maxp:
                s = z; zaehler[(p, k)][s] += 1   # Lichess schreibt Standard SAN
                x = punkte[(p, k)][s]; x[0] += 1; x[1] += pkt
            if struktur and S <= p < S + 6 and b.piece_type_at(mv.from_square) == chess.PAWN:
                if hebel_zug(b, mv): hebel.add(("W" if b.turn == chess.WHITE else "S") + ":" + b.san(mv))
            b.push(mv)
        else:
            p = len(zuege[:max(maxp, S + 6)])
            if L <= p <= maxp: erreicht[(p, epd(b))] += 1
            if p == S: struktur = strukturdaten(b, ich)
        if struktur: strukturen.append((struktur, tuple(sorted(hebel)), pkt))
    fs.fertig()
    daten_bis = [f[8] for f in alle if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", f[8])]
    von, bis = (min(daten_bis), max(daten_bis)) if daten_bis else ("", "")
    print(f"  Partien mit Startzügen: {n_ges}, davon mit Systemregel: {n_sys}, ausgewertet: {n_pool}"
          + (f", Zeitraum {von} bis {bis}" if von else ""), flush=True)
    return {"zaehler": zaehler, "punkte": punkte, "erreicht": erreicht, "alle": alle, "strukturen": strukturen,
            "n_ges": n_ges, "n_sys": n_sys, "n_pool": n_pool, "von": von, "bis": bis}

def hebel_zug(b, mv):
    """Bauernzug, der schlägt oder einen gegnerischen Bauern angreift."""
    if b.is_capture(mv): return True
    b2 = b.copy(); b2.push(mv)
    return any(b2.piece_at(q) and b2.piece_at(q).piece_type == chess.PAWN and b2.piece_at(q).color != b.turn
               for q in b2.attacks(mv.to_square))

def strukturdaten(b, ich):
    zent = lambda farbe: " ".join(chess.square_name(q) for q in sorted(b.pieces(chess.PAWN, farbe), key=lambda q: (chess.square_file(q), q))
                                  if chess.square_file(q) in (2, 3, 4, 5))
    w, s = zent(chess.WHITE), zent(chess.BLACK)
    def roch(farbe):
        k = b.king(farbe); f = chess.square_file(k) if k is not None else 4
        return "kurz" if f >= 6 else ("lang" if f <= 2 else "keine")
    figuren = tuple(sorted(f"{'S' if b.piece_type_at(q) == chess.KNIGHT else 'L'}{chess.square_name(q)}"
                           for q in list(b.pieces(chess.KNIGHT, ich)) + list(b.pieces(chess.BISHOP, ich))))
    return (f"{w} | {s}", epd(b), roch(chess.WHITE) + "/" + roch(chess.BLACK), figuren)

def lade_repertoire(cfg):
    """Alle Stellungen aus der Repertoire PGN: Züge je Stellung, eigene Züge gelten als Repertoirezüge."""
    rep = {}
    if not cfg.get("repertoire_pgn"): return rep
    if not os.path.exists(cfg["repertoire_pgn"]):
        print(f"  Hinweis: Repertoire PGN nicht gefunden ({cfg['repertoire_pgn']}), es geht ohne weiter.", flush=True)
        return rep
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
            for i, v in enumerate(x.variations):
                d = rep.setdefault(k, {}).setdefault(v.move.uci(), {"san": b.san(v.move), "c": "", "rep": False})
                if cfg["repertoire_zuege"] == "alle" or i == 0: d["rep"] = True
                c = filt(v.comment)
                if c and c not in d["c"]: d["c"] = (d["c"] + " " + c).strip()
                st.append(v)
    print(f"  Repertoire PGN: {len(rep)} Stellungen", flush=True)
    return rep

# ---------------------------------------------------------------- Zugbaum
class Baum:
    def __init__(self, cfg, daten, rep):
        self.cfg, self.z, self.rep = cfg, daten["zaehler"], rep
        self.maxp = cfg["bis_zug"] * 2; self.seen = {}; self.knoten_von = {}

    def knoten(self, b, san, art, pfad, **kw):
        mv = b.parse_san(san); b2 = b.copy(); b2.push(mv)
        r = self.rep.get(epd(b), {}).get(mv.uci())
        d = {"san": san, "uci": mv.uci(), "fb": b.fen(), "fa": b2.fen(), "art": art, "rep": False,
             "c": r["c"] if r else "", "kids": [], "transpo": None, "pfad": pfad + [san], "ply": len(pfad) + 1}
        d.update(kw); return d, b2

    def nur_rep(self, b, pfad, lokal):
        out = []
        if len(pfad) >= self.maxp + 6: return out
        for u, r in self.rep.get(epd(b), {}).items():
            mv = chess.Move.from_uci(u); b2 = b.copy(); b2.push(mv)
            if epd(b2) in lokal: continue
            d, _ = self.knoten(b, r["san"], "rep", pfad)
            d["kids"] = self.nur_rep(b2, pfad + [r["san"]], lokal | {epd(b2)})
            out.append(d)
        return out

    def daten(self, b, pfad, erste_ply):
        cfg = self.cfg; k = epd(b); ply = len(pfad)
        c = self.z.get((ply, k)); tot = sum(c.values()) if c else 0
        repz = self.rep.get(k, {})
        picks = []
        if ply < self.maxp and tot >= cfg["min_partien"]:
            rang = c.most_common()
            if b.turn == cfg["ich"]:
                eigene = [r["san"] for r in repz.values() if r["rep"]]
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
            d, b2 = self.knoten(b, m, "daten", pfad, cnt=c[m], anteil=round(100 * c[m] / tot, 1),
                                rep=(b.turn == cfg["ich"] and i > 0))
            if epd(b2) in self.seen: d["transpo"] = self.seen[epd(b2)]
            else:
                self.seen[epd(b2)] = pfad + [m]; self.knoten_von[epd(b2)] = d
                d["kids"] = self.daten(b2, pfad + [m], erste_ply)
            out.append(d)
        if ply < self.maxp:
            for u, r in repz.items():
                if r["san"] in picks: continue
                mv = chess.Move.from_uci(u); b2 = b.copy(); b2.push(mv)
                d, _ = self.knoten(b, r["san"], "rep", pfad, rep=(b.turn == cfg["ich"] and bool(picks) and r["rep"]))
                if epd(b2) in self.seen: d["transpo"] = self.seen[epd(b2)]
                else: d["kids"] = self.nur_rep(b2, pfad + [r["san"]], {epd(b), epd(b2)})
                out.append(d)
        return out

def groesse(d): return 1 + sum(groesse(k) for k in d["kids"])

# ---------------------------------------------------------------- Kapitel
def kapitel_bilden(cfg, wurzel_kids):
    start = cfg["start_san"]; ich = cfg["ich"]
    hv = []; kids = wurzel_kids; pfad = list(start); b = chess.Board()
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
        for k in neben: kap += teilen(cfg, p, k, bb, teil)
        if rest:
            wer = "eigene " if bb.turn == ich else ""
            kap.append({"teil": teil, "name": f"Diverse {wer}{bb.fullmove_number}. Züge", "pfad": p, "eintraege": rest})
    return kap

def teilen(cfg, p, k, bb, teil):
    name = label(bb, k["san"], cfg)
    if groesse(k) <= cfg["kapitel_max"] or not k["kids"] or k["kids"][0]["art"] != "daten":
        return [{"teil": teil, "name": name, "pfad": p, "eintraege": [k]}]
    w = k["kids"][0]; b2 = bb.copy(); b2.push_san(k["san"])
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

def gesamtanteil(c, daten):
    n = sum(daten["erreicht"].get((e["ply"], key(e["fa"])), 0) for e in c["eintraege"] if e["art"] == "daten")
    return 100 * n / daten["n_pool"] if daten["n_pool"] else 0

def kapitel_ordnen(cfg, kapitel, daten):
    """Sortiert nach Gesamtanteil, seltene Kapitel derselben Verzweigung werden zusammengelegt."""
    for c in kapitel:
        c["gruppen"] = [(c["pfad"], c["eintraege"])]
        c["anteil"] = gesamtanteil(c, daten)
        daten_e = [e for e in c["eintraege"] if e["art"] == "daten"]
        if len(c["eintraege"]) == 1 and daten_e:
            c["name"] = zugfolge(c["pfad"] + [daten_e[0]["san"]], cfg)
        else:
            c["name"] = f"{zugfolge(c['pfad'], cfg)}, weitere Züge"
    gross = sorted([c for c in kapitel if c["anteil"] >= cfg["kapitel_min_anteil"]], key=lambda c: -c["anteil"])
    klein = collections.defaultdict(list)
    for c in kapitel:
        if c["anteil"] < cfg["kapitel_min_anteil"]: klein[c["teil"]].append(c)
    zusammen = []
    for _, cs in klein.items():
        if len(cs) == 1: zusammen.append(cs[0]); continue
        gemeinsam = cs[0]["pfad"]
        for c in cs[1:]:
            n = 0
            while n < min(len(gemeinsam), len(c["pfad"])) and gemeinsam[n] == c["pfad"][n]: n += 1
            gemeinsam = gemeinsam[:n]
        zusammen.append({"teil": cs[0]["teil"], "pfad": gemeinsam, "anteil": sum(c["anteil"] for c in cs),
                         "gruppen": [g for c in cs for g in c["gruppen"]], "eintraege": [e for c in cs for e in c["eintraege"]],
                         "name": f"Seltene Abweichungen nach {zugfolge(gemeinsam, cfg) or 'dem Start'} ({len(cs)} Linien)"})
    zusammen.sort(key=lambda c: -c["anteil"])
    return gross + zusammen

def verlaengern(cfg, kapitel, daten, knoten_von):
    """Hauptvariante jedes Eintrags mindestens bis kapitel_min_zug: erst meistgespielte Züge
    (ab verlaengern_min_partien Partien), den Rest rechnet danach Stockfish."""
    ziel = cfg["kapitel_min_zug"] * 2; offen = []
    for c in kapitel:
        for e in c["eintraege"]:
            if e["transpo"]: continue
            node = e
            while node["kids"] and not node["kids"][0]["transpo"]:
                node = node["kids"][0]
            if node["kids"]:
                # Hauptvariante endet in einer Zugumstellung: deren Fortsetzung übernehmen
                node = node["kids"][0]; quelle = knoten_von.get(key(node["fa"])); erst = True
                while quelle and node["ply"] < ziel:
                    nxt = next((k for k in quelle["kids"] if k["art"] == "daten"), None)
                    if not nxt: break
                    d = {"san": nxt["san"], "uci": nxt["uci"], "fb": nxt["fb"], "fa": nxt["fa"], "art": "ext", "rep": False,
                         "kids": [], "transpo": None, "pfad": node["pfad"] + [nxt["san"]], "ply": node["ply"] + 1,
                         "c": "Fortsetzung der Hauptvariante dort:" if erst else ""}
                    node["kids"].insert(0, d); node = d; erst = False
                    quelle = knoten_von.get(key(nxt["fa"])) if nxt["transpo"] else nxt
            ply = node["ply"]; b = chess.Board(node["fa"]); erst = True
            while ply < ziel:
                z = daten["zaehler"].get((ply, epd(b))); tot = sum(z.values()) if z else 0
                if tot < cfg["verlaengern_min_partien"]: break
                m = z.most_common(1)[0][0]; mv = b.parse_san(m); fb = b.fen(); b.push(mv)
                d = {"san": m, "uci": mv.uci(), "fb": fb, "fa": b.fen(), "art": "ext", "rep": False, "kids": [], "transpo": None,
                     "pfad": node["pfad"] + [m], "ply": ply + 1,
                     "c": f"Ab hier weniger als {cfg['min_partien']} Partien, weiter mit dem meistgespielten Zug ({tot} Partien)." if erst else ""}
                node["kids"].insert(0, d); node = d; ply += 1; erst = False
            if ply < ziel: offen.append((node, b.fen(), ziel - ply))
    return offen

def stockfish_anhaengen(cfg, offen, sf):
    for node, fen, n in offen:
        r = sf.get(f"L{cfg['tiefe']}|{key(fen)}|{n}")
        if not r: continue
        b = chess.Board(fen)
        for j, u in enumerate(r["zuege"]):
            mv = chess.Move.from_uci(u); san = b.san(mv); fb = b.fen(); b.push(mv)
            d = {"san": san, "uci": u, "fb": fb, "fa": b.fen(), "art": "ext", "rep": False, "kids": [], "transpo": None,
                 "pfad": node["pfad"] + [san], "ply": node["ply"] + 1, "c": "Ab hier Empfehlung von Stockfish." if j == 0 else ""}
            node["kids"].insert(0, d); node = d
        sf[f"E{cfg['tiefe']}|" + key(b.fen())] = {"s": r["s"], "m": r["m"]}

# ---------------------------------------------------------------- Quickstart
def quickstart_linien(cfg, wurzel, baum):
    """Die wahrscheinlichsten Linien: zuerst die Hauptlinie, dann jeweils die wahrscheinlichste
    Abweichung des Gegners, jede Linie läuft danach mit dem häufigsten Zug weiter."""
    import heapq
    ich = cfg["ich"]; ende = cfg["quickstart_bis_zug"] * 2
    def weiter(k):
        if k["transpo"]:
            n = baum.knoten_von.get(key(k["fa"])); return n["kids"] if n else []
        return k["kids"]
    def lauf(kids, pfad, p, kandidaten):
        while True:
            daten = [k for k in kids if k["art"] == "daten"]
            if not daten or len(pfad) >= ende: return pfad
            b = chess.Board()
            for m in pfad: b.push_san(m)
            if b.turn == ich:
                reps = baum.rep.get(epd(b), {})
                eigen = [k for k in daten if k["rep"]]
                k = daten[0] if (not reps or reps.get(daten[0]["uci"], {}).get("rep") or not eigen) else eigen[0]
            else:
                for alt in daten[1:]:
                    heapq.heappush(kandidaten, (-p * alt["anteil"] / 100, len(kandidaten), weiter(alt), pfad + [alt["san"]]))
                k = daten[0]; p = p * k["anteil"] / 100
            kids = weiter(k); pfad = pfad + [k["san"]]
    kandidaten = []; out = []
    out.append((1.0, lauf(wurzel, list(cfg["start_san"]), 1.0, kandidaten)))
    while kandidaten and len(out) < cfg["quickstart_linien"]:
        np_, _, kids, pfad = heapq.heappop(kandidaten)
        out.append((-np_, lauf(kids, pfad, -np_, kandidaten)))
    return out

# ---------------------------------------------------------------- Fehler des Gegners
def fehler_kandidaten(cfg, kapitel, daten):
    """Je Kapitel die Stellungen, in denen der Gegner zieht, mit den häufigen Zügen."""
    ich = cfg["ich"]; maxp = cfg["bis_zug"] * 2; je_kap = []
    for c in kapitel:
        st = []
        def geh(d):
            if d["art"] != "daten" or d["transpo"]: return
            b = chess.Board(d["fa"])
            if b.turn != ich and d["ply"] < maxp:
                z = daten["zaehler"].get((d["ply"], key(d["fa"])))
                tot = sum(z.values()) if z else 0
                if tot >= cfg["min_partien"]:
                    kand = [(m, n) for m, n in z.items()
                            if n >= cfg["fehler_min_partien"] and 100 * n / tot >= cfg["fehler_min_anteil"]]
                    if kand: st.append((d, tot, kand))
            for k in d["kids"]: geh(k)
        for e in c["eintraege"]: geh(e)
        je_kap.append(st)
    return je_kap

def fehler_auswerten(cfg, kapitel, kandidaten, sf, daten):
    ich = cfg["ich"]; gegner = not ich; liste = []; karte = {}
    for c, st in zip(kapitel, kandidaten):
        funde = []
        for d, tot, kand in st:
            b = chess.Board(d["fa"]); ucis = sorted(b.parse_san(m).uci() for m, _ in kand)
            r = sf.get(f"F{cfg['fehler_tiefe']}|{key(d['fa'])}|{','.join(ucis)}")
            if not r: continue
            vz = 1 if gegner == chess.WHITE else -1
            pz = daten["punkte"].get((d["ply"], key(d["fa"])), {})
            for m, n in kand:
                u = b.parse_san(m).uci(); x = r["kand"].get(u)
                if not x: continue
                verlust = wc(vz * r["s"]) - wc(vz * x["s"])
                if verlust < cfg["fehler_grenze"]: continue
                p = pz.get(m, [0, 0]); rest_n = sum(v[0] for s, v in pz.items() if s != m)
                rest_p = sum(v[1] for s, v in pz.items() if s != m)
                funde.append({"pfad": d["pfad"], "san": m, "uci": u, "n": n, "fb": d["fa"], "vorher": r["s"],
                              "nachher": x["s"], "pv": x["pv"], "nag": 4 if verlust >= 0.3 else 2,
                              "quote": 100 * p[1] / p[0] if p[0] else None,
                              "quote_rest": 100 * rest_p / rest_n if rest_n else None})
        funde.sort(key=lambda f: -f["n"])
        for f in funde: karte[(key(f["fb"]), f["uci"])] = f
        liste.append(funde[:cfg["fehler_anzahl"]])
    return liste, karte

# ---------------------------------------------------------------- Bauernstrukturen
def strukturen_auswerten(cfg, daten):
    rec = daten["strukturen"]
    if not rec: return []
    zaehl = collections.Counter(s[0] for s, _, _ in rec)
    out = []
    for k, n in zaehl.most_common(cfg["strukturen_anzahl"]):
        teil = [(s, h, p) for s, h, p in rec if s[0] == k]
        bsp = collections.Counter(s[1] for s, _, _ in teil).most_common(1)[0][0]
        roch = collections.Counter(s[2] for s, _, _ in teil).most_common(3)
        fig = collections.Counter(f for s, _, _ in teil for f in s[3]).most_common(6)
        heb = collections.Counter(x for _, h, _ in teil for x in h)
        heb_p = collections.defaultdict(float)
        for _, h, p in teil:
            for x in h: heb_p[x] += p
        out.append({"id": k, "n": n, "anteil": 100 * n / len(rec), "quote": 100 * sum(p for _, _, p in teil) / n,
                    "beispiel": bsp, "rochade": [(r, 100 * m / n) for r, m in roch],
                    "figuren": [(f, 100 * m / n) for f, m in fig],
                    "hebel": [(x, 100 * m / n, 100 * heb_p[x] / m) for x, m in heb.most_common(5)]})
    return out

def zentrum(sid):
    w, s = sid.split(" | ")
    return f"Weiß {w or 'ohne'}, Schwarz {s or 'ohne'}"

# ---------------------------------------------------------------- Stockfish
_eng = None
def _init(pfad):
    global _eng
    _eng = chess.engine.SimpleEngine.popen_uci(pfad); _eng.configure({"Threads": 1, "Hash": 64})

def _wert(info): return info["score"].white().score(mate_score=10000)

def _aufgabe(a):
    typ, schluessel = a[0], a[1]
    if typ == "E":
        b = chess.Board(a[2])
        if b.is_game_over():
            o = b.outcome(); return schluessel, {"s": 0 if o.winner is None else (10000 if o.winner else -10000), "m": None}
        i = _eng.analyse(b, chess.engine.Limit(depth=a[3]))
        return schluessel, {"s": _wert(i), "m": i["pv"][0].uci() if i.get("pv") else None}
    if typ == "F":
        b = chess.Board(a[2]); lim = chess.engine.Limit(depth=a[4])
        best = _eng.analyse(b, lim)
        zuege = [chess.Move.from_uci(u) for u in a[3]]
        infos = _eng.analyse(b, lim, multipv=len(zuege), root_moves=zuege)
        if isinstance(infos, dict): infos = [infos]
        kand = {}
        for i in infos:
            if i.get("pv"): kand[i["pv"][0].uci()] = {"s": _wert(i), "pv": [m.uci() for m in i["pv"][1:4]]}
        return schluessel, {"s": max(_wert(best), max((k["s"] for k in kand.values()), default=-99999)) if b.turn == chess.WHITE
                            else min(_wert(best), min((k["s"] for k in kand.values()), default=99999)), "kand": kand}
    if typ == "L":
        b = chess.Board(a[2]); zuege = []
        while len(zuege) < a[3] and not b.is_game_over():
            r = _eng.play(b, chess.engine.Limit(depth=a[4])); zuege.append(r.move.uci()); b.push(r.move)
        if b.is_game_over(): return schluessel, {"zuege": zuege, "s": 0, "m": None}
        i = _eng.analyse(b, chess.engine.Limit(depth=a[4]))
        return schluessel, {"zuege": zuege, "s": _wert(i), "m": i["pv"][0].uci() if i.get("pv") else None}

def stockfish(cfg, aufgaben):
    pfad = cfg["basis"] + "_stockfish.json"
    cache = json.load(open(pfad)) if os.path.exists(pfad) else {}
    offen = [a for a in {a[1]: a for a in aufgaben}.values() if a[1] not in cache]
    print(f"  Stockfish: {len(aufgaben)} Aufgaben, davon neu zu rechnen: {len(offen)}", flush=True)
    if offen:
        fs = Fortschritt("Stockfish", len(offen)); t = time.time()
        with Pool(cfg["prozesse"], initializer=_init, initargs=(cfg["stockfish"],)) as pool:
            for s, r in pool.imap_unordered(_aufgabe, offen, chunksize=2):
                cache[s] = r; fs.schritt()
                if time.time() - t > 60: json.dump(cache, open(pfad, "w")); t = time.time()
        json.dump(cache, open(pfad, "w")); fs.fertig()
    return cache

# ---------------------------------------------------------------- Musterpartien
def musterpartien(cfg, alle, ziele):
    """Je Endstellung die Partie mit dem höchsten Elo Schnitt und die eigenen Folgezüge aller Partien
    (für den typischen Aufbau aus der Praxis)."""
    best = {}; folgen = collections.defaultdict(list)
    maxp = cfg["bis_zug"] * 2; ich = cfg["ich"]; nplan = cfg["plan_zuege"]
    fs = Fortschritt("Musterpartien", len(alle))
    for f in alle:
        fs.schritt()
        try: schnitt = (int(f[3]) + int(f[4])) / 2
        except ValueError: continue
        pkt = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}.get(f[5], 0.5)
        if ich == chess.BLACK: pkt = 1 - pkt
        b = chess.Board(); verlauf = []
        for z in f[11].split()[:maxp + 2 * nplan]:     # auch hinter dem Linienende, für die Folgezüge
            try: mv = b.parse_san(z.rstrip("?!"))
            except ValueError: break
            eigen = b.turn == ich; san = b.san(mv); nr = b.fullmove_number
            b.push(mv); verlauf.append((epd(b), mv.uci(), san, eigen, nr))
        for i, (k, _, _, _, _) in enumerate(verlauf):
            if k not in ziele: continue
            if k not in best or schnitt > best[k][0]:
                d = f[8]; ort = f[0].replace("https://", "")
                best[k] = (schnitt, f"{f[5]} ({(int(f[9]) + 1) // 2}) {f[1]} ({f[3]}) gegen {f[2]} ({f[4]}), Lichess {d[5:7]}.{d[:4]}, {ort}")
            eigene = [(u, s, nr) for _, u, s, e, nr in verlauf[i + 1:] if e and "x" not in s][:nplan]   # Schlagzüge sind Reaktionen, kein Aufbau
            if eigene: folgen[k].append((eigene, pkt))
    fs.fertig()
    print(f"  Musterpartien: {len(best)} von {len(ziele)} Endstellungen", flush=True)
    plaene = {}
    for k, liste in folgen.items():
        n = len(liste)
        if n < cfg["plan_min_partien"]: continue
        q0 = sum(p for _, p in liste) / n
        zaehl = collections.defaultdict(lambda: [0, 0.0, 0, "", 0])   # Partien, Punkte, Summe Position, SAN, Zugnummer
        for eigene, p in liste:
            gesehen = set()
            for pos, (u, s, nr) in enumerate(eigene):
                if u in gesehen: continue
                gesehen.add(u); z = zaehl[u]; z[0] += 1; z[1] += p; z[2] += pos; z[3] = s; z[4] = nr
        kand = [(u, z) for u, z in zaehl.items() if z[0] >= 2 and z[0] / n >= 0.2]
        kand.sort(key=lambda x: -(x[1][1] + 3 * q0) / (x[1][0] + 3))      # geglättete Quote, kleine Zahlen zählen weniger
        wahl = []; felder = set()
        for u, z in kand:                       # pro Feld nur ein Zug, z. B. nicht b5 und b6 oder Sc6 und c6 zugleich
            if u[:2] in felder or u[2:4] in felder: continue    # auch nicht zwei Züge auf dasselbe Feld
            felder.update((u[:2], u[2:4])); wahl.append((u, z))
            if len(wahl) == nplan: break
        wahl.sort(key=lambda x: x[1][2] / x[1][0])                         # in typischer Reihenfolge
        if wahl: plaene[k] = {"n": n, "zuege": [(u, z[3]) for u, z in wahl]}
    print(f"  Typischer Aufbau aus der Praxis: {len(plaene)} Endstellungen", flush=True)
    return {k: v[1] for k, v in best.items()}, plaene

# ---------------------------------------------------------------- PGN
def winkel(cp):
    e = cp / 100
    if abs(e) < 0.3: return 11
    if e >= 1.5: return 18
    if e >= 0.7: return 16
    if e > 0: return 14
    if e <= -1.5: return 19
    if e <= -0.7: return 17
    return 15

def pfeil(u):
    m = chess.Move.from_uci(u)
    return f"[%cal G{chess.square_name(m.from_square)}{chess.square_name(m.to_square)}]"

def blaetter(d, out):
    if not d["kids"] and not d["transpo"]: out.add(d["fa"])
    for k in d["kids"]: blaetter(k, out)

def datum_de(d):
    j, m, t = d.split(".")
    return f"{int(t)}.{int(m)}.{j}"

def neues_spiel(cfg, titel, fen=None):
    heute = datetime.date.today().strftime("%Y.%m.%d")
    g = chess.pgn.Game(); g.headers.clear()
    # Kapitelname nur in Event und ChapterName, ohne White/Black Tags. Sonst zeigen
    # Lichess und En Croissant den Namen als "Titel - ?" an.
    for k, v in (("Event", titel), ("Site", "?"), ("Date", heute), ("Round", "?"),
                 ("Result", "*"), ("ECO", cfg["eco"]), ("Annotator", "repertoire.py (Lichess, Stockfish)"),
                 ("PlyCount", "0"), ("SourceTitle", cfg["titel"]), ("SourceVersionDate", heute)):
        g.headers[k] = v
    g.headers["ChapterName"] = titel
    if fen: g.setup(chess.Board(fen))
    return g

def speichern(pfad, spiele):
    with open(pfad, "w", encoding="utf-8", newline="\r\n") as f:
        for g in spiele:
            g.headers["PlyCount"] = str(len(list(g.mainline_moves())))
            print(g, file=f, end="\n\n")

class Schreiber:
    def __init__(self, cfg, kapitel, sf, muster, fehler_karte):
        self.cfg, self.sf, self.muster, self.fk = cfg, sf, muster, fehler_karte
        self.plaene = {}
        self.praefixe = [(p + [e["san"]], i) for i, c in enumerate(kapitel, 2) for p, es in c.get("gruppen", [(c["pfad"], c["eintraege"])]) for e in es]
        self.neben = collections.defaultdict(list)
        for f in fehler_karte.values(): self.neben[key(f["fb"])].append(f)

    def verweis(self, p):
        best = None
        for pre, i in self.praefixe:
            if len(pre) <= len(p) and p[:len(pre)] == pre and (best is None or len(pre) > len(best[0])): best = (pre, i)
        txt = zugfolge(p, self.cfg)
        return f"Zugumstellung, siehe Kapitel {best[1]:02d} nach {txt}." if best else f"Zugumstellung zur Stellung nach {txt}."

    def ende(self, node, fen, mit_partie=True):
        teile = []; r = self.sf.get(f"E{self.cfg['tiefe']}|" + key(fen))
        plan = self.plaene.get(key(fen))
        if r and r["s"] is not None:
            node.nags.add(winkel(r["s"]))
            if r["m"] and not plan: teile.append(pfeil(r["m"]))
        if plan:
            pf = ",".join(f"B{u[:2]}{u[2:4]}" for u, _ in plan["zuege"])
            zuege = ", ".join(de(s, self.cfg) for _, s in plan["zuege"])
            teile.append(f"[%cal {pf}] Typischer Aufbau aus der Praxis ({plan['n']} Partien): {zuege}.")
        if mit_partie and key(fen) in self.muster: teile.append(self.muster[key(fen)])
        return teile

    def fehler_text(self, f):
        t = f"Fehler: Stockfish {ev(f['vorher'])} auf {ev(f['nachher'])}."
        if f["quote"] is not None and f["quote_rest"] is not None:
            t += (f" {seite(self.cfg['ich'])} punktet {zahl(f['quote'], 0)} % nach diesem Zug, "
                  f"{zahl(f['quote_rest'], 0)} % nach den übrigen Zügen.")
        return t

    def widerlegung(self, node, fen, pv):
        b = chess.Board(fen); n = node
        for i, u in enumerate(pv):
            mv = chess.Move.from_uci(u)
            if mv not in b.legal_moves: break
            n = n.add_variation(mv); b.push(mv)
            if i == 0: n.comment = "Widerlegung laut Stockfish"

    def neben_fehler(self, node, fen, vorhanden):
        for f in self.neben.get(key(fen), []):
            if f["uci"] in vorhanden: continue
            ch = node.add_variation(chess.Move.from_uci(f["uci"])); ch.nags.add(f["nag"])
            ch.comment = self.fehler_text(f)
            b = chess.Board(fen); b.push(chess.Move.from_uci(f["uci"]))
            self.widerlegung(ch, b.fen(), f["pv"])

    def add(self, gn, d, mit_partie=True, fehler=True):
        ch = gn.add_variation(chess.Move.from_uci(d["uci"])); teile = []
        f = self.fk.get((key(d["fb"]), d["uci"])) if fehler else None
        if f: ch.nags.add(f["nag"]); teile.append(self.fehler_text(f))
        if d.get("rep"): teile.append("Repertoirezug")
        if self.cfg["statistik"] and d["art"] == "daten": teile.append(f"{zahl(d['anteil'])} %, {d['cnt']} Partien")
        if d["c"]: teile.append(d["c"])
        if d["transpo"]: teile.append(self.verweis(d["transpo"]))
        elif not d["kids"]:
            teile += self.ende(ch, d["fa"], mit_partie)
            if f: self.widerlegung(ch, d["fa"], f["pv"])
        ch.comment = " ".join(teile)
        for k in d["kids"]: self.add(ch, k, mit_partie, fehler)
        if fehler and not d["transpo"]: self.neben_fehler(ch, d["fa"], {k["uci"] for k in d["kids"]})
        return ch

def zuege_setzen(g, pfad):
    b = chess.Board(); n = g
    for m in pfad: mv = b.parse_san(m); b.push(mv); n = n.add_variation(mv)
    return n, b

def kurz(d, ply, bis):
    e = dict(d); e["c"] = ""; e["rep"] = d["rep"]
    e["kids"] = [kurz(k, ply + 1, bis) for k in d["kids"] if k["art"] == "daten"] if ply + 1 < bis else []
    if ply + 1 >= bis: e["transpo"] = None
    return e

# ---------------------------------------------------------------- Hauptprogramm
def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    t0 = time.time(); cfg = lade_config(sys.argv[1]); ich = cfg["ich"]
    print("1/6 Daten", flush=True)
    daten = lade_partien(cfg)
    rep = lade_repertoire(cfg)
    print("2/6 Zugbaum und Kapitel", flush=True)
    b = chess.Board()
    for m in cfg["start_san"]: b.push_san(m)
    L = len(cfg["start_san"]); erste = L if b.turn != ich else L + 1
    baum = Baum(cfg, daten, rep); baum.seen[epd(b)] = list(cfg["start_san"])
    wurzel = baum.daten(b, list(cfg["start_san"]), erste)
    kapitel = kapitel_ordnen(cfg, kapitel_bilden(cfg, wurzel), daten)
    intro = list(cfg["start_san"]); kids = wurzel
    while kids and kids[0]["art"] == "daten" and not kids[0]["transpo"]:
        intro.append(kids[0]["san"]); kids = kids[0]["kids"]
    zus = [kurz(k, 0, cfg["zusammenfassung_bis_zug"] * 2 - L) for k in wurzel if k["art"] == "daten"]
    linien = quickstart_linien(cfg, wurzel, baum)
    strukturen = strukturen_auswerten(cfg, daten)
    kandidaten = fehler_kandidaten(cfg, kapitel, daten) if cfg["fehler"] else [[] for _ in kapitel]
    offen = verlaengern(cfg, kapitel, daten, baum.knoten_von)
    print(f"  {len(kapitel)} Kapitel im Hauptteil, {len(linien)} Quickstart Linien, {len(strukturen)} Strukturen", flush=True)

    print("3/6 Stockfish", flush=True)
    fens = set()
    for c in kapitel:
        for e in c["eintraege"]: blaetter(e, fens)
    for e in zus: blaetter(e, fens)
    bb = chess.Board()
    for m in intro: bb.push_san(m)
    fens.add(bb.fen())
    start_sf = {f for _, f, _ in offen}
    aufgaben = [("E", f"E{cfg['tiefe']}|" + key(f), f, cfg["tiefe"]) for f in fens if f not in start_sf]
    for _, f, n in offen:
        aufgaben.append(("L", f"L{cfg['tiefe']}|{key(f)}|{n}", f, n, cfg["tiefe"]))
    for st in kandidaten:
        for d, tot, kand in st:
            bx = chess.Board(d["fa"]); ucis = sorted(bx.parse_san(m).uci() for m, _ in kand)
            aufgaben.append(("F", f"F{cfg['fehler_tiefe']}|{key(d['fa'])}|{','.join(ucis)}", d["fa"], ucis, cfg["fehler_tiefe"]))
    q_ende = cfg["quickstart_bis_zug"] * 2
    for p, pfad in linien:
        bx = chess.Board()
        for m in pfad: bx.push_san(m)
        aufgaben.append(("L", f"L{cfg['tiefe']}|{key(bx.fen())}|{q_ende - len(pfad)}", bx.fen(), max(q_ende - len(pfad), 0), cfg["tiefe"]))
    sf = stockfish(cfg, aufgaben)
    stockfish_anhaengen(cfg, offen, sf)
    fens = set()
    for c in kapitel:
        for e in c["eintraege"]: blaetter(e, fens)
    for e in zus: blaetter(e, fens)
    fens.add(bb.fen())

    print("4/6 Fehler des Gegners und Musterpartien", flush=True)
    fehler_liste, fehler_karte = fehler_auswerten(cfg, kapitel, kandidaten, sf, daten) if cfg["fehler"] else ([[] for _ in kapitel], {})
    print(f"  {len(fehler_karte)} häufige Fehler gefunden", flush=True)
    muster, plaene = musterpartien(cfg, daten["alle"], {key(f) for f in fens})

    print("5/6 Repertoire schreiben", flush=True)
    w = Schreiber(cfg, kapitel, sf, muster, fehler_karte); w.plaene = plaene
    gegner = seite(not ich)
    info = (f"{cfg['titel']}. Repertoire für {seite(ich)}, Startzüge {de(cfg['start'], cfg)}. "
            f"Daten: {daten['n_ges']} Lichess Partien"
            + (f" vom {datum_de(daten['von'])} bis {datum_de(daten['bis'])}" if daten["von"] else "")
            + f", davon {daten['n_pool']} ausgewertet. "
            f"REGELN: Bei jedem Zug von {gegner} die {cfg['antworten']} meistgespielten Antworten, in den Zügen "
            f"{', '.join(map(str, cfg['fruehe_zuege_ab_5_prozent']))} zusätzlich jede ab 5 %. Bei {seite(ich)} ist der meistgespielte Zug Hauptvariante, "
            f"der Repertoirezug steht markiert daneben. Eine Linie verzweigt, solange mindestens {cfg['min_partien']} Partien die Stellung erreichen, "
            f"höchstens bis Zug {cfg['bis_zug']}. Die Prozentzahl im Kapitelnamen ist der Anteil aller ausgewerteten Partien, die das Kapitel erreichen, die Kapitel sind danach sortiert. "
            f"Kapitel unter {zahl(cfg['kapitel_min_anteil'], 0)} % sind je Verzweigung als seltene Abweichungen am Ende zusammengefasst. "
            f"Die Hauptvariante jedes Kapitels läuft mindestens bis Zug {cfg['kapitel_min_zug']}: erst mit dem meistgespielten Zug, solange mindestens "
            f"{cfg['verlaengern_min_partien']} Partien die Stellung erreichen, danach mit dem besten Zug laut Stockfish (jeweils kommentiert). "
            f"Zugumstellungen verweisen auf das Kapitel, in dem die Stellung zuerst vorkommt. "
            f"FEHLER: Am Ende jedes Kapitels stehen die häufigsten Fehler von {gegner}. Als Fehler zählt ein Zug, der laut Stockfish mindestens "
            f"{zahl(cfg['fehler_grenze'])} Gewinnchancen kostet (Skala von minus 1 bis plus 1 wie bei Lichess, in ausgeglichenen Stellungen etwa ein Bauer). "
            f"? Fehler, ?? grober Fehler, dazu die Widerlegung. "
            f"AM LINIENENDE: Bewertung von Stockfish (Tiefe {cfg['tiefe']}, aus Sicht von Weiß): = ausgeglichen, ⩲ oder ⩱ leichter Vorteil, "
            f"± oder ∓ klarer Vorteil, +- oder -+ entscheidender Vorteil. Blaue Pfeile = typischer Aufbau aus der Praxis: die nächsten {cfg['plan_zuege']} eigenen Züge ohne Schlagzüge, in typischer Reihenfolge, mit denen {seite(ich)} nach dieser Stellung am besten gepunktet hat (mindestens {cfg['plan_min_partien']} Partien). Gibt es dafür zu wenige Partien, zeigt ein grüner Pfeil den besten Zug laut Stockfish. "
            f"Musterpartie = Lichess Partie mit dem höchsten Elo Schnitt, die die Stellung erreicht hat.")
    spiele = []
    g = neues_spiel(cfg, "01 Intro"); g.comment = info
    n, bb = zuege_setzen(g, intro); n.comment = " ".join(w.ende(n, bb.fen()))
    spiele.append(g)
    for i, (c, fl) in enumerate(zip(kapitel, fehler_liste), 2):
        pz = gesamtanteil(c, daten)
        anteil = f" ({zahl(pz)} % gesamt)" if pz >= 0.1 else (" (unter 0,1 % gesamt)" if pz > 0 else "")
        g = neues_spiel(cfg, f"{i:02d} {c['name']}{anteil}")
        n0, b0 = zuege_setzen(g, c["pfad"])
        for p, es in c["gruppen"]:
            n = n0; bx = b0.copy()
            for m in p[len(c["pfad"]):]:
                mv = bx.parse_san(m); bx.push(mv)
                n = next((v for v in n.variations if v.move == mv), None) or n.add_variation(mv)
            for e in es: w.add(n, e)
        if fl:
            teile = []
            for j, f in enumerate(fl, 1):
                b0 = chess.Board(f["fb"])
                teile.append(f"{j}) {label(b0, f['san'], cfg)}{'??' if f['nag'] == 4 else '?'} in {f['n']} Partien, "
                             f"nach {zugfolge(f['pfad'], cfg, len(c['pfad']))}. {w.fehler_text(f)}")
            ende = g.end()
            ende.comment = (ende.comment + " " if ende.comment else "") + f"HÄUFIGSTE FEHLER VON {gegner.upper()} IN DIESEM KAPITEL: " + " ".join(teile)
        spiele.append(g)
    nr = len(kapitel) + 2
    texte = json.load(open(cfg["strukturen_text"], encoding="utf-8")) if cfg.get("strukturen_text") and os.path.exists(cfg["strukturen_text"]) else {}
    vergeben = set()
    for s in strukturen:
        g, s["name"], s["merkmale"] = strukturmodul.kapitel(s, nr, cfg, ich, neues_spiel, de, zahl, seite, texte, vergeben)
        spiele.append(g); nr += 1
    for p in cfg["anhang_pgn"]:
        if not os.path.exists(p):
            print(f"  Hinweis: Anhang nicht gefunden ({p}), wird übersprungen.", flush=True); continue
        h = open(p, encoding="utf-8-sig")
        while True:
            g0 = chess.pgn.read_game(h)
            if g0 is None: break
            titel = (g0.headers.get("ChapterName") or g0.headers.get("Black", "?").strip("?")
                     or g0.headers.get("White", "?").strip("?") or g0.headers.get("Event", "?"))
            titel = re.sub(r"^\d+ ", "", titel)
            g = neues_spiel(cfg, f"{nr:02d} {titel}"); g.comment = g0.comment
            def kopie(src, dst):
                for v in src.variations:
                    x = dst.add_variation(v.move); x.comment = v.comment; x.nags = set(v.nags); kopie(v, x)
            kopie(g0, g); spiele.append(g); nr += 1
    g = neues_spiel(cfg, f"{nr:02d} Zusammenfassung")
    n, _ = zuege_setzen(g, cfg["start_san"])
    for e in zus: w.add(n, e, mit_partie=False, fehler=False)
    spiele.append(g)
    speichern(cfg["ausgabe"], spiele)
    print(f"  Geschrieben: {cfg['ausgabe']} ({len(spiele)} Kapitel)", flush=True)

    print("6/6 Quickstart und Strukturdatei", flush=True)
    q = []
    for i, (p, pfad) in enumerate(linien, 1):
        g = neues_spiel(cfg, f"{i:02d} {zugfolge(pfad[:8], cfg)}")
        n, bx = zuege_setzen(g, pfad)
        r = sf.get(f"L{cfg['tiefe']}|{key(bx.fen())}|{q_ende - len(pfad)}")
        if r:
            for j, u in enumerate(r["zuege"]):
                n = n.add_variation(chess.Move.from_uci(u))
                if j == 0: n.comment = "Ab hier Empfehlung von Stockfish."
            if r["s"] is not None:
                n.nags.add(winkel(r["s"]))
                if r["m"]: n.comment = (n.comment + " " + pfeil(r["m"])).strip()
        q.append(g)
    speichern(cfg["basis"] + "_quickstart.pgn", q)
    json.dump([{"id": s["id"], "name": s.get("name"), "zentrum": zentrum(s["id"]), "merkmale": s.get("merkmale", []), "beispiel_fen": s["beispiel"], "partien": s["n"],
                "anteil_prozent": round(s["anteil"], 1), "quote_prozent": round(s["quote"], 1), "rochaden": s["rochade"],
                "figuren": s["figuren"], "hebel": s["hebel"], "text": texte.get(s["id"], "")} for s in strukturen],
              open(cfg["basis"] + "_strukturen.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  Geschrieben: {cfg['basis']}_quickstart.pgn ({len(q)} Linien), {cfg['basis']}_strukturen.json", flush=True)
    print(f"Fertig, Gesamtdauer {dauer(time.time() - t0)}", flush=True)

if __name__ == "__main__":
    main()
