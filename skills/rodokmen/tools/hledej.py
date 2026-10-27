#!/usr/bin/env python3
"""Hledání v datech projektu – místo grepu: osobu vypíše celou, nevadí diakritika ani velká písmena.

Použití (z kořene projektu):
  python3 -I tools/hledej.py <text> [další text …] [--kde osoby|zapisy|texty|svazky|mista|dokumenty] [--vse]
    text    část slova bez ohledu na diakritiku a velikost písmen: „plachetk“ najde Plachetka, Plachetková, Plachetkovi;
            víc textů = všechny musí být v téže položce („plachetk ostasov“ = Plachetkové v Ostašovicích)
    --kde   jen jedna skupina (jde zopakovat): osoby = předci, boční příbuzní, rody, otázky, hypotézy (osoby.json);
            zapisy = zaznamy.json a prepisy.json; texty = markdown v data/ (deník, údaje od rodiny, dotazy, stav,
            zajímavosti, příběh); svazky, mista, dokumenty = stejnojmenné soubory JSON
    --vse   všechny shody (jinak nejvýš 30 v každé skupině)
Předka vypíše se vším (roky, stav, fakta, zápisy, poznámka) a s tím, čí je otec nebo matka; zápis s klíčem a shrnutím;
z markdownu odstavec nebo řádek tabulky zkrácený kolem shody. Nic nemění. Návratový kód 1, když nic nenajde.
"""
import json, os, sys, unicodedata
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I složku skriptu do sys.path nepřidá
from nacti_osoby import nacti_osoby

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SKUPINY = ("osoby", "zapisy", "texty", "svazky", "mista", "dokumenty")
TEXTY = ("research_log.md", "udaje_od_rodiny.md", "archivni_dotazy.md", "STAV.md", "zajimavosti.md", "pribeh.md")
LIMIT = 30


def norm_mapa(s):
    """Text bez diakritiky a velkých písmen + pro každý znak pozice v původním textu (kvůli výřezu kolem shody)."""
    out, idx = [], []
    for i, ch in enumerate(s):
        for c in unicodedata.normalize("NFKD", ch.casefold()):
            if not unicodedata.combining(c):
                out.append(c)
                idx.append(i)
    return "".join(out), idx


def norm(s):
    return norm_mapa(s)[0]


def texty_v(v):
    """Všechny texty (i čísla) z hodnoty JSON, rekurzivně."""
    if isinstance(v, dict):
        return [t for x in v.values() for t in texty_v(x)]
    if isinstance(v, list):
        return [t for x in v for t in texty_v(x)]
    return [] if v is None else [str(v)]


def sedi(text, hledane):
    n = norm(text)
    return all(h in n for h in hledane)


def vyrez(text, hledane, okoli=110):
    """Dlouhý text zkrácený kolem první shody."""
    text = " ".join(text.split())
    if len(text) <= 2 * okoli + 40:
        return text
    n, idx = norm_mapa(text)
    i = min((n.find(h) for h in hledane if h in n), default=0)
    a = idx[max(0, i - okoli)] if idx else 0
    b = idx[min(len(idx) - 1, i + okoli)] + 1 if idx else len(text)
    return ("…" if a > 0 else "") + text[a:b].strip() + ("…" if b < len(text) else "")


def radek(*casti):
    return " · ".join(str(c) for c in casti if c not in (None, "", []))


def osoby(ns, hledane):
    P = ns.get("P", {})
    for k, p in P.items():
        if not isinstance(p, dict) or not sedi(" ".join(texty_v(p)), hledane):
            continue
        dite = P.get(k // 2) if isinstance(k, int) and k > 1 else None
        vztah = f"{'otec' if k % 2 == 0 else 'matka'} P {k // 2} {dite.get('n', '')}" if isinstance(dite, dict) else ""
        out = [radek(f"P {k}", p.get("n"), p.get("y"), p.get("st"), vztah)]
        if p.get("f"):
            out.append("    " + " | ".join(p["f"]))
        if p.get("r"):
            out.append("    zápisy: " + ", ".join(p["r"]))
        if p.get("note"):
            out.append("    pozn.: " + vyrez(p["note"], hledane, 300))
        ostatni = {x: v for x, v in p.items() if x not in ("n", "y", "st", "f", "r", "note")}
        if ostatni:
            out.append("    " + ", ".join(f"{x}: {v}" for x, v in ostatni.items()))
        yield "\n".join(out)
    for s in ns.get("SIDE", []):
        if not isinstance(s, dict) or not sedi(" ".join(texty_v(s)), hledane):
            continue
        predek = P.get(s.get("k"), {})
        out = [radek("boční", s.get("n"), s.get("v"), s.get("y"), s.get("st"),
                     f"u P {s.get('k')} {predek.get('n', '') if isinstance(predek, dict) else ''}".strip())]
        if s.get("f"):
            out.append("    " + " | ".join(s["f"]))
        if s.get("t"):
            out.append("    " + vyrez(s["t"], hledane, 300))
        if s.get("r"):
            out.append("    zápisy: " + ", ".join(s["r"]))
        yield "\n".join(out)
    for k, v in ns.get("LINES", {}).items():
        if sedi(" ".join(texty_v(v)), hledane):
            yield radek(f"rod {k}", *texty_v(v))
    for q in ns.get("ISSUES", []):
        text = q if isinstance(q, str) else " – ".join(texty_v(q))
        if sedi(text, hledane):
            yield "otázka: " + vyrez(text, hledane, 200)
    for h in ns.get("HYPOTEZY", []):
        if isinstance(h, dict) and sedi(" ".join(texty_v(h)), hledane):
            yield radek(f"hypotéza (rod {h.get('rod')})", h.get("nadpis")) + "\n    " + vyrez(h.get("text", ""), hledane, 200)


def zapisy(hledane):
    for z in jload("zaznamy.json", []):
        if isinstance(z, dict) and sedi(" ".join(texty_v(z)), hledane):
            out = radek(f"zápis {z.get('klic')}", z.get("nazev"), z.get("datum"),
                        f"svazek {z.get('svazek')}, snímek {z.get('snimek')}" if z.get("svazek") else "")
            yield out + ("\n    " + vyrez(z["shrnuti"], hledane, 200) if z.get("shrnuti") else "")
    for k, v in jload("prepisy.json", {}).items():
        texty = [t for t in texty_v(v) if sedi(t, hledane)] or ([" ".join(texty_v(v))] if sedi(k + " " + " ".join(texty_v(v)), hledane) else [])
        if texty:
            yield f"přepis {k}\n    " + vyrez(texty[0], hledane, 200)


def slovnik(soubor, nazev, pole, hledane):
    d = jload(soubor, {})
    for k, v in (d.items() if isinstance(d, dict) else enumerate(d)):
        if sedi(f"{k} " + " ".join(texty_v(v)), hledane):
            yield radek(f"{nazev} {k}" if isinstance(d, dict) else nazev,
                        *[vyrez(str(v.get(p)), hledane, 120) for p in pole if isinstance(v, dict) and v.get(p)])


def texty(hledane):
    """Markdown po odstavcích; řádek tabulky (deník výzkumu) je samostatná položka."""
    for f in TEXTY:
        path = os.path.join(DATA, f)
        if not os.path.exists(path):
            continue
        blok, zacatek = [], 0
        lines = open(path, encoding="utf-8-sig").read().splitlines() + [""]
        for i, line in enumerate(lines, 1):
            tabulka = line.lstrip().startswith("|")
            if blok and (not line.strip() or tabulka):
                text = " ".join(blok)
                if sedi(text, hledane):
                    yield f"{f}:{zacatek}: " + vyrez(text, hledane)
                blok = []
            if tabulka:
                if sedi(line, hledane) and not set(line) <= set("|-: "):
                    yield f"{f}:{i}: " + vyrez(line, hledane)
            elif line.strip():
                if not blok:
                    zacatek = i
                blok.append(line.strip())


def jload(name, default):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    try:
        return json.load(open(path, encoding="utf-8-sig"))
    except ValueError as e:
        print(f"POZOR: data/{name} nejde přečíst ({e}) – přeskočeno", file=sys.stderr)
        return default


def main():
    args, kde, vse = [], [], False
    it = iter(sys.argv[1:])
    for a in it:
        if a == "--vse":
            vse = True
        elif a == "--kde":
            kde.append(next(it, ""))
        else:
            args.append(a)
    hledane = [norm(a) for a in args if a.strip()]
    if not hledane or any(k not in SKUPINY for k in kde):
        sys.exit(__doc__)

    zdroje = {"osoby": None, "zapisy": lambda: zapisy(hledane), "texty": lambda: texty(hledane),
              "svazky": lambda: slovnik("svazky.json", "svazek", ("svazek", "archiv", "popis"), hledane),
              "mista": lambda: slovnik("mista.json", "místo", ("osm",), hledane),
              "dokumenty": lambda: slovnik("dokumenty.json", "dokument", ("img", "popis", "osoby"), hledane)}
    try:
        ns = nacti_osoby(DATA)
        zdroje["osoby"] = lambda: osoby(ns, hledane)
    except (OSError, ValueError) as e:
        print(f"POZOR: osoby.json nejde přečíst ({e}) – osoby přeskočeny", file=sys.stderr)
        zdroje["osoby"] = lambda: iter(())

    celkem = 0
    for skupina in SKUPINY:
        if kde and skupina not in kde:
            continue
        nalezy = list(zdroje[skupina]())
        if not nalezy:
            continue
        celkem += len(nalezy)
        print(f"== {skupina} ({len(nalezy)})")
        for n in nalezy if vse else nalezy[:LIMIT]:
            print(n)
        if not vse and len(nalezy) > LIMIT:
            print(f"… a dalších {len(nalezy) - LIMIT} (--vse vypíše všechny, víc slov hledání zúží)")
    if not celkem:
        print(f"Nic nenalezeno: {' '.join(args)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
