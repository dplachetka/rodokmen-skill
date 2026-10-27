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


def tvar(ns):
    """Tvar sekcí osoby.json – špatný tvar by shodil zbytek kontroly i export webu (npm run data)."""
    chyby = []
    seznam_textu = lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v)
    for k, p in (ns.get("P") or {}).items():
        if not isinstance(p, dict) or not isinstance(p.get("n"), str):
            chyby.append(f"P {k}: osoba musí být objekt aspoň se jménem n, je {str(p)[:60]!r}")
            continue
        for pole in ("f", "r"):
            if pole in p and not seznam_textu(p[pole]):
                chyby.append(f"P {k} ({p['n']}): {pole} musí být seznam textů")
        if not isinstance(p.get("y", ""), str):
            chyby.append(f"P {k} ({p['n']}): y musí být text (\"1850–1910\", \"* 1895\")")
    for i, s in enumerate(ns.get("SIDE") or []):
        if not isinstance(s, dict) or not isinstance(s.get("n"), str) or "k" not in s:
            chyby.append(f"SIDE #{i + 1}: musí být objekt s k (číslo předka) a n (jméno), je {str(s)[:60]!r}")
        elif any(pole in s and not seznam_textu(s[pole]) for pole in ("f", "r")):
            chyby.append(f"SIDE {s['n']}: f a r musí být seznamy textů")
    for k, v in (ns.get("LINES") or {}).items():
        if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, str) for x in v)):
            chyby.append(f"LINES {k}: musí být [název rodu, jedna věta], je {str(v)[:60]!r}")
    for i, q in enumerate(ns.get("ISSUES") or []):
        if not (isinstance(q, str) or isinstance(q, list) and len(q) == 2 and all(isinstance(x, str) for x in q)):
            chyby.append(f"ISSUES #{i + 1}: musí být [otázka, odpověď], je {str(q)[:60]!r}")
    for i, h in enumerate(ns.get("HYPOTEZY") or []):
        if not isinstance(h, dict):
            chyby.append(f"HYPOTEZY #{i + 1}: musí být objekt {{\"rod\": 8, \"nadpis\": …, \"text\": …}}, je {str(h)[:60]!r}")
        elif not isinstance(h.get("nadpis", ""), str) or not isinstance(h.get("text", ""), str) \
                or not all(isinstance(x, list) and len(x) == 2 for x in h.get("polozky", [])) or not seznam_textu(h.get("zaznamy", [])):
            chyby.append(f"HYPOTEZY #{i + 1} ({h.get('nadpis', '?')}): nadpis a text jsou texty, polozky dvojice [jméno, text], zaznamy klíče")
    return chyby


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
    spatne = tvar(ns)
    if spatne:
        for e in spatne:
            print("CHYBA:", e)
        sys.exit("Opravte tvar data/osoby.json (reference/data.md), jinak nepůjde ani npm run data.")
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
        y = (p.get("y") or "").strip()
        if not y and any(f.strip().startswith("*") and re.search(r"\d{4}", f) for f in p.get("f", [])):
            warn.append(f"osoba {k} ({p.get('n')}): fakta mají narození, ale y je prázdné – web ukáže osobu bez roku")
        elif re.fullmatch(r"(asi\s+)?\d{4}", y):
            warn.append(f"osoba {k} ({p.get('n')}): y \"{y}\" je nejasné – narození, nebo úmrtí? Napiš \"* {y}\", \"† {y}\" nebo rozsah")
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
        # sourozenec se má dát později převést na osobu s rodiči: pohlaví a u nevlastních společný rodič (data.md)
        v, chybi = (s.get("v") or "").strip().lower(), []
        if re.match(r"(nevlastní\s+)?sourozenec\b", v):
            chybi.append("napiš bratr, nebo sestra (podle jména či zápisu)")
        if re.match(r"nevlastní\s+(bratr|sestra|sourozenec)\b", v) and not re.search(r"\(stejn[áý] (matka|otec)\)", v):
            chybi.append("podle křtu doplň společného rodiče: „(stejná matka)“, nebo „(stejný otec)“")
        if chybi:
            warn.append(f"boční příbuzný '{s.get('n')}' (u P {s.get('k')}), vztah „{s.get('v')}“: {'; '.join(chybi)} "
                        f"– ať jde později převést na osobu s rodiči (reference/data.md)")
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
        # J = jiný pramen: rodinný doklad (křestní list, dopis) online snímek nemá
        if z.get("druh") != "J" and not z.get("odkaz") and not svazky.get(z.get("svazek", ""), {}).get("url"):
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

    # Nedávné = osoba narozená 1870 a později (její potomci žijí); bez roku narození podle roků v textu (posledních ~100 let).
    # Staré matriční údaje (nemanželské dítě v 18. stol.) nevadí, ani když poznámka zmíní sčítání 1921.
    hranice = datetime.date.today().year - 100

    def recent(text, narozen=None, vychozi=False):
        if narozen:
            return narozen >= 1870
        return vychozi or any(int(y) >= hranice for y in re.findall(r"\b(19\d\d|20\d\d)\b", text))
    otazka = lambda x: re.sub(r"[:\s]+", " ", (x if isinstance(x, str) else x[0]))[:40].strip()   # stálý název i po přidání otázek
    texty = [(f"otázka {otazka(x)}", x if isinstance(x, str) else " ".join(x), None, False) for x in ns.get("ISSUES", [])]
    for k, p in P.items():
        text = " ".join(p.get("f", [])) + " " + p.get("note", "")
        texty.append((f"osoba {k}", text, rok_narozeni(p.get("y", ""), p.get("f", []), p.get("n", "")), k < 8))
    texty += [(f"boční příbuzný {s.get('n')}", " ".join([s.get("n", ""), s.get("t", "")] + s.get("f", [])),
               rok_narozeni(s.get("y", ""), s.get("f", []), s.get("n", "")), False) for s in SIDE]
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
            texty += [(f, odst, None, False) for odst in open(os.path.join(DATA, f), encoding="utf-8").read().split("\n\n")]
    # co uživatel výslovně schválil ke zveřejnění, web.json → "citlive_schvaleno", dvojí tvar:
    # místo a slovo ("osoba 26: nemanželsk", "*: dluh", jen místo "osoba 26" = všechna slova v něm),
    # nebo úryvek textu se slovem ("oběsil se ve stodole") – platí jen pro to místo v textu; po změně textu se hlásí znovu
    schvaleno = cfg.get("citlive_schvaleno") or []
    if isinstance(schvaleno, str):   # jediná položka zapsaná bez hranatých závorek
        schvaleno = [schvaleno]
    schvaleno = [s.strip() for s in (schvaleno if isinstance(schvaleno, list) else [])
                 if isinstance(s, str) and len(s.strip()) >= 3]
    schvaleno_mala = {s.lower() for s in schvaleno}

    def schvalene(kde, text, m):
        slovo = m.group(0).lower()
        if {kde.lower(), f"{kde.lower()}: {slovo}", f"*: {slovo}"} & schvaleno_mala:
            return True
        for s in schvaleno:
            i = text.find(s)
            while i >= 0:
                if i <= m.start() and m.end() <= i + len(s):
                    return True
                i = text.find(s, i + 1)
        return False
    for kde, text, narozen, vychozi in texty:
        if not recent(text, narozen, vychozi):
            continue
        m = next((m for m in citlive.finditer(text) if not schvalene(kde, text, m)), None)
        if m:
            warn.append(f"CITLIVÉ ({kde}): „…{text[max(0, m.start() - 40):m.end() + 40].strip()}…“ – jde na web; zeptej se uživatele, "
                        f"jestli to tam smí být (reference/soukromi.md). Schválí-li to, přidej do seznamu v data/web.json "
                        f"\"citlive_schvaleno\": [\"{kde}: {m.group(0).lower()}\"] (nebo úryvek textu s tím slovem)")

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
