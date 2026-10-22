#!/usr/bin/env python3
"""Kontrola konzistence dat rodokmenu. Spouštějte po každé větší změně a před stavbou webu.

Použití: kontrola.py
Vypíše CHYBY (rozbijí web nebo jsou věcně špatně) a UPOZORNĚNÍ (něco chybí, doplnit).
Návratový kód 1, pokud jsou chyby.
"""
import datetime, json, os, re, sys
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I složku skriptu do sys.path nepřidá
from nacti_osoby import SEKCE, nacti_osoby, roky_ve_jmene

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def jload(name, default):
    p = os.path.join(DATA, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


STAVY = ("doc", "prob", "fam", "mh", "unk")


def rok_narozeni(y, facts, name):
    """Rok narození z y („* 1931“, „asi 1844–1900“), z faktu „* 30. 3. 1931 …“ nebo ze jména „Josef X (* 1931)“."""
    m = roky_ve_jmene(name)
    for text in [y or ""] + [f.strip() for f in facts if f.strip().startswith("*")] + [m[1] if m else ""]:
        if text and not text.lstrip().startswith(("†", "?")):
            r = re.search(r"\d{4}", text)
            if r:
                return int(r.group(0))
    return None


def zemrel(y, facts, name):
    m = roky_ve_jmene(name)
    jmeno = m[1] if m else ""
    return any("†" in t for t in [y or "", jmeno] + list(facts)) \
        or any(re.search(r"\d{4}\s*[–-]\s*\S", t) for t in (y or "", jmeno))


def zijici(kde, y, facts, name, texts):
    """Žijící lidé smí být na webu jen se jménem a rokem narození (reference/soukromi.md)."""
    rok = rok_narozeni(y, facts, name)
    if not rok or rok <= datetime.date.today().year - 100 or zemrel(y, facts, name):
        return None
    text = " ".join(texts)
    letos = str(datetime.date.today().year)   # „zjištěno 22. 10. 2026“ je datum poznámky, ne údaj o člověku
    m = next((m for m in re.finditer(r"\b\d{1,2}\.\s*\d{1,2}\.\s*(\d{4})|\bč(?:p|\.\s*p)?\.?\s*\d+", text)
              if m.group(1) != letos), None)
    if m:
        return (f"ŽIJÍCÍ? ({kde}, nar. {rok}, bez úmrtí): „…{text[max(0, m.start() - 30):m.end() + 20].strip()}…“ jde na web – "
                f"u žijících jen jméno a rok narození (reference/soukromi.md); zemřel-li, doplň † do y nebo do faktů")
    return None


def main():
    err, warn = [], []
    try:
        ns = nacti_osoby(DATA)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"CHYBA: data/osoby.json nejde načíst: {e}")
    for name in ns:
        if name not in SEKCE:
            err.append(f"osoby.json: neznámá sekce '{name}' – platné jsou {', '.join(SEKCE)}")
    P, SIDE, LINES, SAME = ns.get("P", {}), ns.get("SIDE", []), ns.get("LINES", {}), ns.get("SAME", {})
    zaz = jload("zaznamy.json", [])
    svazky, prep, hl = jload("svazky.json", {}), jload("prepisy.json", {}), jload("zvyrazneni.json", {})
    keys = [z.get("klic") for z in zaz]
    dup = {k for k in keys if keys.count(k) > 1}
    if dup:
        err.append(f"zápisy se stejným klíčem: {sorted(dup)}")
    keys = set(keys)

    if 1 not in P:
        err.append("chybí osoba 1 (výchozí osoba rodokmenu)")
    for k, p in P.items():
        if not isinstance(k, int) or k < 1:
            err.append(f"osoba {k!r}: číslo musí být kladné celé číslo")
            continue
        if k > 1 and k // 2 not in P and k not in SAME:
            warn.append(f"osoba {k} ({p.get('n')}): v rodokmenu chybí její dítě {k // 2} – je číslo správně?")
        st = p.get("st", "unk")
        if st not in STAVY:
            err.append(f"osoba {k}: neznámý stav '{st}'")
        if p.get("sour") not in (None, "hotovo", "částečně"):
            err.append(f"osoba {k}: sour='{p.get('sour')}' – povolené je „hotovo“ nebo „částečně“ (nebo nic)")
        for r in p.get("r", []):
            if r not in keys:
                err.append(f"osoba {k} ({p.get('n')}) cituje neexistující zápis '{r}'")
        if st == "doc" and not p.get("r"):
            warn.append(f"osoba {k} ({p.get('n')}) je 'doc' (doloženo), ale necituje žádný zápis")
    for s in SIDE:
        if s.get("k") not in P:
            err.append(f"boční příbuzný '{s.get('n')}' patří k neexistující osobě {s.get('k')}")
        for r in s.get("r", []):
            if r not in keys:
                err.append(f"boční příbuzný '{s.get('n')}' cituje neexistující zápis '{r}'")
        if s.get("st") and s["st"] not in STAVY:
            err.append(f"boční příbuzný '{s.get('n')}': neznámý stav '{s['st']}'")
        if s.get("st") == "doc" and not s.get("r"):
            warn.append(f"boční příbuzný '{s.get('n')}' je 'doc' (doloženo), ale necituje žádný zápis")
        if not s.get("y") and roky_ve_jmene(s.get("n", "")):
            warn.append(f"boční příbuzný '{s.get('n')}': roky jsou ve jméně – přesuň je do 'y' "
                        f"(python3 -I tools/nacti_osoby.py sourozenci)")
    bez_vztahu = [s.get("n", "?") for s in SIDE if not s.get("v")]
    if bez_vztahu:
        warn.append(f"{len(bez_vztahu)} bočních záznamů nemá vztah 'v' (např. {', '.join(bez_vztahu[:3])}) – na webu jsou ve skupině "
                    f"„Vztah zatím neuveden“; doplň v (bratr, sestra, manželka, strýc…, nebo u nepříbuzných učeň, kmotr, soused…)")
    for a, c in SAME.items():
        if c not in P:
            err.append(f"SAME: {a} -> {c}, ale osoba {c} neexistuje")
    for k in LINES:
        if k not in range(8, 16):
            err.append(f"LINES: rod {k} – rody mají čísla 8 až 15 (pradědečci a prababičky)")

    cited = {r for p in P.values() for r in p.get("r", [])} | {r for s in SIDE for r in s.get("r", [])}
    for z in zaz:
        k = z.get("klic", "?")
        for f in ("klic", "druh", "datum", "nazev", "shrnuti"):
            if not z.get(f):
                err.append(f"zápis {k}: chybí pole '{f}'")
        if z.get("svazek") and z["svazek"] not in svazky:
            err.append(f"zápis {k}: svazek '{z['svazek']}' není v data/svazky.json")
        if z.get("ukazka"):   # vymyšlený zápis ukázkové rodiny – nemá snímek ani přepis
            continue
        if not z.get("odkaz") and not svazky.get(z.get("svazek", ""), {}).get("url"):
            warn.append(f"zápis {k}: chybí odkaz na snímek (pole 'odkaz')")
        if not os.path.exists(os.path.join(ROOT, "vyrezy", k + ".jpg")):
            warn.append(f"zápis {k}: chybí výřez vyrezy/{k}.jpg")
        elif k not in hl:
            warn.append(f"zápis {k}: chybí rámeček (tools/ramecek.py)")
        if k not in prep:
            warn.append(f"zápis {k}: chybí přepis a překlad v data/prepisy.json")
        if k not in cited:
            warn.append(f"zápis {k}: necituje ho žádná osoba (doplnit do 'r' u osoby nebo bočního příbuzného)")

    for name, e in jload("mista.json", {}).items():
        if "lat" not in e:
            warn.append(f"místo {name}: nemá souřadnice (spusťte tools/mista.py)")
        try:
            re.compile(e.get("re") or "")
        except re.error as ex:
            err.append(f"místo {name}: špatný výraz '{e.get('re')}': {ex}")

    cfg = jload("web.json", {})
    if not (cfg.get("prihlaseni") or {}).get("odpoved") and not (cfg.get("prihlaseni") or {}).get("otevreny"):
        warn.append("web.json: není nastavená odpověď na přihlašovací otázku – nasazení webu skončí chybou")

    if re.search(r"Novák|Petrovi", json.dumps(cfg, ensure_ascii=False)) and "Novák" not in P.get(1, {}).get("n", ""):
        warn.append("web.json: jsou v něm ještě ukázkové texty (Novákovi) – nastav název, příběh a kontakt")

    # Citlivé věci, které jdou na web: ISSUES („Co hledáme“), poznámky a fakta osob, boční příbuzní, texty.
    citlive = re.compile(r"sebevra|vzal[a]? si život|oběsil|zastřelil[a]? se|utopil[a]? se|alkohol|vězen|kriminál|"
                         r"rozvod|rozvedl|psychiatr|léčebn|duševn|rakovin|nemanželsk|cizoložst|dluh|exekuc|interrupc|potrat", re.I)

    def recent(text):   # 20. století a později – staré matriční údaje (nemanželské dítě v 18. stol.) nevadí
        return any(int(y) >= 1900 for y in re.findall(r"\b(19\d\d|20\d\d)\b", text))
    texty = [("ISSUES", i if isinstance(i, str) else " ".join(i)) for i in ns.get("ISSUES", [])]
    for k, p in P.items():
        text = " ".join(p.get("f", [])) + " " + p.get("note", "")
        roky = [int(y) for y in re.findall(r"\b1[5-9]\d\d|20\d\d\b", p.get("y", "") + " " + text)]
        texty.append((f"osoba {k}", text + (" 1900" if roky and min(roky) >= 1870 or k < 8 else "")))
    texty += [(f"boční příbuzný {s.get('n')}", " ".join([s.get("n", ""), s.get("t", "")] + s.get("f", []))) for s in SIDE]
    for k, p in P.items():
        w = zijici(f"osoba {k} {p.get('n')}", p.get("y", ""), p.get("f", []), p.get("n", ""), p.get("f", []) + [p.get("note", "")])
        if w:
            warn.append(w)
    for s in SIDE:
        w = zijici(f"boční příbuzný {s.get('n')}", s.get("y", ""), s.get("f", []), s.get("n", ""), [s.get("t", "")] + s.get("f", []))
        if w:
            warn.append(w)
    for f in ("zajimavosti.md", "pribeh.md"):
        if os.path.exists(os.path.join(DATA, f)):
            texty += [(f, odst) for odst in open(os.path.join(DATA, f), encoding="utf-8").read().split("\n\n")]
    for kde, text in texty:
        m = citlive.search(text)
        if m and recent(text):
            warn.append(f"CITLIVÉ ({kde}): „…{text[max(0, m.start() - 40):m.end() + 40].strip()}…“ – jde na web; "
                        f"zeptej se uživatele, jestli to tam smí být (reference/soukromi.md)")

    if not os.path.exists(os.path.join(DATA, "pribeh.md")) and LINES:
        hlavni = min(LINES)
        n = max((k.bit_length() for k in P if k >= 8 and k >> (k.bit_length() - 4) == hlavni), default=0)
        if n >= 6:
            warn.append(f"rod {LINES[hlavni][0]} má už {n} generací – je čas napsat příběh rodu "
                        f"(data/pribeh.md, reference/pribehy.md); koncept nejdřív ukaž uživateli v chatu")

    log = os.path.join(DATA, "research_log.md")
    rows = sum(1 for l in open(log, encoding="utf-8") if re.match(r"^\| \d+ \|", l)) if os.path.exists(log) else 0
    print(f"{len(P)} osob, {len(zaz)} zápisů, {len(svazky)} svazků, {rows} řádků deníku")
    for e in err:
        print("CHYBA:", e)
    for w in warn:
        print("upozornění:", w)
    if not err and not warn:
        print("Vše v pořádku.")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
