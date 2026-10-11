"""Bauernstrukturen lesbar machen: bekannte Strukturen benennen, Merkmale einer Stellung
beschreiben und ein Kapitel mit Markierungen und Varianten auf dem Brett bauen.

Die Ideentexte sind allgemeine Lehrbuchpläne und gelten für die Struktur, nicht für jede
einzelne Stellung. Erkannt wird nur an der Bauernstellung, Figuren spielen keine Rolle.
"""
import chess, chess.pgn

W, S = chess.WHITE, chess.BLACK

def _bauern(b, farbe):
    return {chess.square_name(q) for q in b.pieces(chess.PAWN, farbe)}

def _linie(felder, linie):
    return [f for f in felder if f[0] == linie]

def _hat(felder, *qs): return all(q in felder for q in qs)
def _ohne(felder, *linien): return not any(f[0] in linien for f in felder)

# (Name, Prüfung, Ideen). Reihenfolge zählt: speziellere Strukturen zuerst.
STRUKTUREN = [
    ("Isolierter Damenbauer bei Weiß",
     lambda w, s: len(_linie(w, "d")) == 1 and _ohne(w, "c", "e"),
     "Weiß spielt aktiv: Springer nach e5, Läufer auf die Diagonale b1-h7, Turm auf die e-Linie und Angriff am Königsflügel. "
     "Der Durchbruch d4-d5 öffnet das Spiel. Schwarz blockiert auf d5, am besten mit einem Springer, tauscht Figuren und zielt "
     "auf das Endspiel, in dem der isolierte Bauer schwach wird."),
    ("Isolierter Damenbauer bei Schwarz",
     lambda w, s: len(_linie(s, "d")) == 1 and _ohne(s, "c", "e"),
     "Schwarz spielt aktiv: Springer nach e4, Druck über die e- und c-Linie, Durchbruch ...d5-d4. Weiß blockiert auf d4, "
     "tauscht Figuren und zielt auf das Endspiel gegen den schwachen Bauern."),
    ("Hängende Bauern bei Weiß",
     lambda w, s: _hat(w, "c4", "d4") and _ohne(w, "b", "e"),
     "Die Bauern c4 und d4 geben Weiß Raum und Spiel im Zentrum, der Vorstoß d4-d5 ist der typische Durchbruch. "
     "Schwarz greift die Bauern über die c- und d-Linie an und versucht, einen davon zum Vorrücken zu zwingen, damit Felder frei werden."),
    ("Hängende Bauern bei Schwarz",
     lambda w, s: _hat(s, "c5", "d5") and _ohne(s, "b", "e"),
     "Die Bauern c5 und d5 geben Schwarz Raum, der Vorstoß ...d5-d4 ist der typische Durchbruch. Weiß setzt die Bauern über "
     "die c- und d-Linie unter Druck."),
    ("Stonewall mit Weiß",
     lambda w, s: _hat(w, "d4", "e3", "f4"),
     "Weiß kontrolliert e5 und stellt dort gern einen Springer hin. Typisch ist ein Königsangriff mit Dame über e1 nach h4 oder g3, "
     "Turm über f3 nach h3 und dem Vorstoß g4-g5. Problemfigur ist der eigene Läufer c1, er wird oft über b2 oder d2-e1 aktiviert. "
     "Das Feld e4 ist ein Loch, Schwarz stellt dort gern einen Springer hin und spielt am Damenflügel mit ...c5 oder ...b5."),
    ("Stonewall mit Schwarz",
     lambda w, s: _hat(s, "d5", "e6", "f5"),
     "Schwarz kontrolliert e4 und stellt dort gern einen Springer hin, oft folgt ein Angriff am Königsflügel. Problemfigur ist der "
     "Läufer c8. Weiß nutzt das Loch auf e5, tauscht gern den schwarzfeldrigen Läufer und spielt am Damenflügel mit c4 oder b4."),
    ("Carlsbad (Damengambit mit Abtausch)",
     lambda w, s: _hat(w, "d4") and _ohne(w, "c") and _hat(s, "c6", "d5") and _ohne(s, "e"),
     "Weiß spielt den Minoritätsangriff b4-b5, um auf c6 eine Schwäche zu schaffen, oder bereitet e3-e4 im Zentrum vor. "
     "Schwarz sucht Spiel am Königsflügel, oft mit Springer nach e4 und dem Vorstoß ...f5."),
    ("Carlsbad mit vertauschten Farben",
     lambda w, s: _hat(s, "d5") and _ohne(s, "c") and _hat(w, "c3", "d4") and _ohne(w, "e"),
     "Schwarz spielt den Minoritätsangriff ...b5-b4 gegen c3. Weiß sucht Spiel am Königsflügel, oft mit Springer nach e5 und f2-f4."),
    ("Geschlossener Damenflügel mit c5",
     lambda w, s: _hat(w, "c5", "d4") and _hat(s, "c6", "d5"),
     "Weiß hat mit c5 Raum am Damenflügel und spielt dort mit b4-b5. Schwarz greift die Kette mit ...b6 an oder öffnet mit ...e5 das Zentrum."),
    ("Geschlossener Damenflügel mit ...c4",
     lambda w, s: _hat(s, "c4", "d5") and _hat(w, "c3", "d4"),
     "Schwarz hat mit ...c4 Raum am Damenflügel und spielt dort mit ...b5-b4. Weiß greift die Kette mit b3 an oder öffnet mit e3-e4 das Zentrum."),
    ("Symmetrisch mit offener c-Linie",
     lambda w, s: _hat(w, "d4") and _hat(s, "d5") and _ohne(w, "c") and _ohne(s, "c") and not _ohne(w, "e") and not _ohne(s, "e"),
     "Eine ruhige, symmetrische Struktur. Wer die offene c-Linie zuerst mit den Türmen besetzt, steht meist besser. "
     "Die Springer zielen auf die Felder c5 und e5 beziehungsweise c4 und e4, oft entscheidet die aktivere Figurenstellung."),
    ("Zentrumsmehrheit für Weiß",
     lambda w, s: not _ohne(w, "d") and not _ohne(w, "e") and _ohne(w, "c") and _ohne(s, "d") and not _ohne(s, "e"),
     "Weiß hat zwei Zentrumsbauern gegen einen und will mit e3-e4 und d4-d5 das Zentrum öffnen. Schwarz hat dafür die Mehrheit am "
     "Damenflügel, hält die Felder d5 und e4 mit Figuren unter Kontrolle und spielt ...c5 oder ...b5."),
    ("Zentrumsmehrheit für Schwarz",
     lambda w, s: not _ohne(s, "d") and not _ohne(s, "e") and _ohne(s, "c") and _ohne(w, "d") and not _ohne(w, "e"),
     "Schwarz hat zwei Zentrumsbauern gegen einen und will mit ...e5 und ...d4 das Zentrum öffnen. Weiß hat dafür die Mehrheit am "
     "Damenflügel, hält die Felder d4 und e5 mit Figuren unter Kontrolle und spielt c4 oder b4."),
    ("Französische Struktur",
     lambda w, s: _hat(w, "d4", "e5") and _hat(s, "d5", "e6"),
     "Weiß hat Raum am Königsflügel und greift dort an, oft mit f4-f5. Schwarz greift die Kette mit ...c5 an der Basis an und "
     "ergänzt mit ...f6. Problemfigur für Schwarz ist der Läufer c8."),
    ("Königsindische Struktur",
     lambda w, s: _hat(w, "d5", "e4") and _hat(s, "d6", "e5"),
     "Das Zentrum ist geschlossen, beide spielen auf dem Flügel, auf den ihre Bauernkette zeigt: Weiß am Damenflügel mit c4-c5, "
     "Schwarz am Königsflügel mit ...f5 und oft ...g5."),
    ("Benoni Struktur",
     lambda w, s: _hat(w, "d5") and _hat(s, "c5", "d6") and _ohne(s, "e"),
     "Weiß hat Raum im Zentrum und sucht den Durchbruch e4-e5. Schwarz hat die Mehrheit am Damenflügel und spielt ...b5, "
     "der Läufer auf g7 drückt auf die lange Diagonale."),
    ("Maroczy Struktur",
     lambda w, s: _hat(w, "c4", "e4") and _ohne(w, "d") and _hat(s, "d6") and _ohne(s, "c"),
     "Weiß hat Raum und kontrolliert d5, Schwarz steht eng. Schwarz sucht Befreiung mit ...b5 oder ...f5, manchmal ...d5. "
     "Weiß verhindert die Hebel und nutzt den Raumvorteil."),
    ("Sizilianische Struktur",
     lambda w, s: _hat(w, "e4") and _ohne(w, "d") and _hat(s, "d6") and _ohne(s, "c"),
     "Schwarz hat die halboffene c-Linie und spielt am Damenflügel, Hebel sind ...d5 und ...b5. Weiß hat Raum und greift oft am "
     "Königsflügel an, mit f4-f5 oder g4."),
    ("Holländische Struktur mit vertauschten Farben",
     lambda w, s: _hat(w, "f4") and not _hat(w, "d4") and not _hat(w, "e4"),
     "Weiß kontrolliert e5 mit f4. Typisch sind der Läufer b2 auf der langen Diagonale, ein Springer auf e5 und ein Königsangriff "
     "mit Dame über e1 nach h4 oder g3. Der zentrale Hebel ist e3-e4. Weiß achtet auf die Schwächen auf e3 und der Diagonale e1-h4."),
    ("Holländische Struktur",
     lambda w, s: _hat(s, "f5") and not _hat(s, "d5") and not _hat(s, "e5"),
     "Schwarz kontrolliert e4 mit f5, oft folgen ...Lb7 und ein Angriff am Königsflügel mit ...De8-h5. Der zentrale Hebel ist ...e5. "
     "Weiß greift mit e2-e4 im Zentrum an."),
    ("Colle oder London Dreieck",
     lambda w, s: _hat(w, "c3", "d4", "e3") and not _hat(w, "f4"),
     "Ein sehr solider Aufbau. Weiß spielt auf e5 mit einem Springer und bereitet den Hebel e3-e4 vor. Schwarz sucht Spiel mit ...c5 "
     "und ...e5."),
    ("Slawische Struktur",
     lambda w, s: _hat(s, "c6", "d5") and _hat(w, "c4", "d4"),
     "Schwarz steht solide. Die Hebel sind ...e5 oder ...c5, oft nach ...dxc4. Weiß hat etwas mehr Raum und spielt e3-e4."),
    ("Caro-Kann Struktur",
     lambda w, s: _hat(s, "c6", "d5") and _hat(w, "d4") and _ohne(w, "e"),
     "Schwarz steht solide, der Hebel ist ...c5. Weiß hat etwas mehr Raum und den Vorposten e5, oft mit Plänen am Königsflügel."),
    ("Damengambit Struktur",
     lambda w, s: _hat(w, "c4", "d4") and _hat(s, "d5", "e6"),
     "Die Spannung zwischen c4 und d5 prägt das Spiel. Nach cxd5 exd5 entsteht die Carlsbad Struktur. Schwarz befreit sich mit "
     "...c5 oder ...e5."),
    ("Offenes Zentrum",
     lambda w, s: _ohne(w, "d", "e") and _ohne(s, "d", "e"),
     "Ohne Zentrumsbauern zählen Entwicklung und Figurenaktivität. Offene Linien gehören den Türmen, das Läuferpaar ist stark."),
]

def erkennen(b):
    w, s = _bauern(b, W), _bauern(b, S)
    for name, pruef, ideen in STRUKTUREN:
        try:
            if pruef(w, s): return name, ideen
        except Exception:
            continue
    return None, None

def merkmale(b):
    """Kurze Sätze zu isolierten, doppelten und freien Bauern, offenen Linien und Vorposten."""
    saetze = []
    for farbe, name in ((W, "Weiß"), (S, "Schwarz")):
        eigene = b.pieces(chess.PAWN, farbe); fremde = b.pieces(chess.PAWN, not farbe)
        linien = [chess.square_file(q) for q in eigene]
        iso = sorted({chess.square_name(q) for q in eigene
                      if not any(chess.square_file(p) in (chess.square_file(q) - 1, chess.square_file(q) + 1) for p in eigene)})
        doppel = sorted({chess.FILE_NAMES[f] for f in linien if linien.count(f) > 1})
        frei = []
        for q in eigene:
            f, r = chess.square_file(q), chess.square_rank(q)
            vor = [p for p in fremde if abs(chess.square_file(p) - f) <= 1 and
                   (chess.square_rank(p) > r if farbe == W else chess.square_rank(p) < r)]
            if not vor: frei.append(chess.square_name(q))
        halb = [chess.FILE_NAMES[f] for f in range(8) if f not in linien and any(chess.square_file(p) == f for p in fremde)]
        vorposten = []
        for f in range(1, 7):
            for r in ((4, 5) if farbe == W else (3, 2)):
                q = chess.square(f, r)
                gedeckt = any(chess.square_file(p) in (f - 1, f + 1) and chess.square_rank(p) == (r - 1 if farbe == W else r + 1) for p in eigene)
                angreifbar = any(chess.square_file(p) in (f - 1, f + 1) and
                                 (chess.square_rank(p) > r if farbe == W else chess.square_rank(p) < r) for p in fremde)
                if gedeckt and not angreifbar: vorposten.append(chess.square_name(q))
        teile = []
        if iso: teile.append("isolierter Bauer " + ", ".join(iso) if len(iso) == 1 else "isolierte Bauern " + ", ".join(iso))
        if doppel: teile.append("Doppelbauern auf der " + " und ".join(f"{d}-Linie" for d in doppel))
        if frei: teile.append("Freibauer " + ", ".join(frei) if len(frei) == 1 else "Freibauern " + ", ".join(frei))
        if halb: teile.append("halboffene " + ", ".join(f"{h}-Linie" for h in halb))
        if vorposten: teile.append("Vorposten für Springer auf " + ", ".join(vorposten[:3]))
        if teile: saetze.append(f"{name}: " + "; ".join(teile) + ".")
    offen = [chess.FILE_NAMES[f] for f in range(8) if not any(chess.square_file(p) == f for p in b.pieces(chess.PAWN, W) | b.pieces(chess.PAWN, S))]
    if offen: saetze.append("Offene Linien: " + ", ".join(f"{o}-Linie" for o in offen) + ".")
    return saetze

def _rochade(r):
    w, s = r.split("/")
    wort = {"kurz": "kurz", "lang": "lang", "keine": "noch nicht"}
    if w == s: return f"beide Seiten {wort.get(w, w)} rochiert"
    return f"Weiß {wort.get(w, w)} und Schwarz {wort.get(s, s)} rochiert"

def kapitel(s, titel_nr, cfg, ich, neues_spiel, de, zahl, seite, texte, vergeben=None):
    """Ein Kapitel je Struktur: Beispielstellung mit Markierungen, Hebel als Pfeile und Varianten."""
    fen = s["beispiel"] + f" 0 {cfg['strukturen_zug'] + 1}"
    b = chess.Board(fen)
    name, ideen = erkennen(b)
    w, sw = s["id"].split(" | ")
    zentrum = f"Weiß {w or 'ohne'}, Schwarz {sw or 'ohne'}"
    titel = name or zentrum
    if vergeben is not None:
        if name and name in vergeben: titel = f"{name} ({zentrum})"
        vergeben.add(name)
    g = neues_spiel(cfg, f"{titel_nr:02d} Struktur: {titel}", fen=fen)
    teile = [f"STRUKTUR: {name or 'ohne festen Namen'} (Zentrumsbauern {zentrum}). "
             f"Kommt in {zahl(s['anteil'])} % der Partien vor, die Zug {cfg['strukturen_zug']} erreichen ({s['n']} Partien), "
             f"{seite(ich)} punktet {zahl(s['quote'], 0)} %."]
    if s["rochade"]:
        r, p = s["rochade"][0]; teile.append(f"Am häufigsten haben {_rochade(r)} ({zahl(p, 0)} %).")
    if ideen: teile.append("IDEEN: " + ideen)
    if s["id"] in texte: teile.append("EIGENE NOTIZ: " + texte[s["id"]])
    m = merkmale(b)
    if m: teile.append("IN DER BEISPIELSTELLUNG: " + " ".join(m))
    # Markierungen: typische Felder der eigenen Leichtfiguren, Pfeile für Bauernhebel
    grundfelder = {"b1", "c1", "f1", "g1"} if ich == W else {"b8", "c8", "f8", "g8"}
    felder = [f[1:] for f, p in s["figuren"] if p >= 30 and f[1:] not in grundfelder][:4]
    pfeile = []; varianten = []
    for x, a, q in s["hebel"]:
        farbe = W if x[0] == "W" else S; san = x[2:]
        bx = b.copy(); bx.turn = farbe
        try: mv = bx.parse_san(san)
        except ValueError: continue
        pfeile.append(f"{'G' if farbe == ich else 'R'}{chess.square_name(mv.from_square)}{chess.square_name(mv.to_square)}")
        if farbe == b.turn: varianten.append((mv, san, a, q))
    marken = ""
    if felder: marken += "[%csl " + ",".join("Y" + f for f in felder) + "]"
    if pfeile: marken += "[%cal " + ",".join(pfeile) + "]"
    legende = []
    if felder: legende.append("gelb die typischen Felder deiner Leichtfiguren")
    if pfeile: legende.append("Pfeile die häufigsten Bauernhebel der nächsten drei Züge, grün deine, rot die des Gegners")
    if legende: teile.append("Auf dem Brett: " + ", ".join(legende) + ".")
    g.comment = (marken + " " + " ".join(teile)).strip()
    for mv, san, a, q in varianten:
        v = g.add_variation(mv)
        v.comment = f"Hebel {de(san, cfg)}: in {zahl(a, 0)} % der Partien, {seite(ich)} punktet danach {zahl(q, 0)} %."
    return g, name, m
