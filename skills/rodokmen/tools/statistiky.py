#!/usr/bin/env python3
"""Statistiky rodokmenu pro web: čte web/src/data/site.json (předky a zápisy z exportu) a zapíše
web/src/data/statistiky.json. Volá ho tools/export_web.py na konci exportu; jde spustit i samostatně.

Počítá se z faktů předků (pole `facts`; jména i ze sourozenců): narození „* 12. 3. 1873 Obec čp. 5“ (i jen rok „* 1873“), úmrtí „† 14. 5. 1902“
(i s věkem „† 1902 (54 let)“), sňatek „× 28. 1. 1897 Obec Jméno“, věk „(24 let při sňatku)“, povolání podle klíčových slov,
církve podle slov „církev, vyznání“. Bez přesného data se věk počítá z let a je jen přibližný (na webu „≈“).
Počet dětí v rodině a dětská úmrtnost jen z rodin, kde má předek "sour": "hotovo" (všichni sourozenci dohledáni):
děti = předek a jeho vlastní sourozenci (`bratr`, `sestra`, ne nevlastní ani nejistí).
"""
import json, math, os, re, sys
from collections import Counter, defaultdict
from datetime import date

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "web", "src", "data", "site.json")
OUT = os.path.join(ROOT, "web", "src", "data", "statistiky.json")
MISTA = os.path.join(ROOT, "data", "mista.json")

DATE = r"(\d{1,2})\.\s*(?:\((\d{1,2})\.\?\)|(\d{1,2}))\.\s*(\d{4})"
MESICE = ["leden", "únor", "březen", "duben", "květen", "červen", "červenec", "srpen", "září", "říjen", "listopad", "prosinec"]

# klíčové slovo (začátek slova, malými písmeny – „Kovář“ s velkým je příjmení) → (povolání, skupina);
# rozhoduje první shoda v pořadí seznamu, proto obecná slova (dělník, mistr) až nakonec
POVOLANI = [
    ("tkad", "tkadlec", "řemeslo"), ("tkalc", "tkadlec", "řemeslo"), ("soukeník", "soukeník", "řemeslo"),
    ("obuvn", "obuvník", "řemeslo"), ("švec", "obuvník", "řemeslo"), ("krejč", "krejčí", "řemeslo"),
    ("kovář", "kovář", "řemeslo"), ("kolář", "kolář", "řemeslo"), ("zedník", "zedník", "řemeslo"), ("tesař", "tesař", "řemeslo"),
    ("truhlář", "truhlář", "řemeslo"), ("bednář", "bednář", "řemeslo"), ("sklenář", "sklenář", "řemeslo"),
    ("hrnčíř", "hrnčíř", "řemeslo"), ("jirchář", "jirchář", "řemeslo"), ("koželuh", "koželuh", "řemeslo"),
    ("mlynář", "mlynář", "řemeslo"), ("pekař", "pekař", "řemeslo"), ("řezník", "řezník", "řemeslo"), ("sládek", "sládek", "řemeslo"),
    ("sedlák", "sedlák", "zemědělství"), ("rolník", "rolník", "zemědělství"), ("hospodář", "hospodář", "zemědělství"),
    ("chalupník", "chalupník", "zemědělství"), ("domkář", "domkář", "zemědělství"), ("podsedník", "podsedník", "zemědělství"),
    ("familiant", "familiant", "zemědělství"), ("výměnk", "výměnkář", "zemědělství"), ("na výměnku", "výměnkář", "zemědělství"),
    ("podruh", "podruh", "zemědělství"), ("čeledín", "čeledín", "zemědělství"), ("děveč", "děvečka", "zemědělství"),
    ("zahradník", "zahradník", "zemědělství"), ("pastýř", "pastýř", "zemědělství"), ("ovčák", "ovčák", "zemědělství"),
    ("hajný", "hajný", "les"), ("myslivec", "myslivec", "les"), ("lesník", "lesník", "les"), ("lesní", "lesník", "les"),
    ("strojvůd", "strojvůdce", "doprava"), ("výpravčí", "výpravčí", "doprava"), ("průvodčí", "průvodčí", "doprava"),
    ("železničář", "železničář", "doprava"), ("na dráze", "železničář", "doprava"), ("při dráze", "železničář", "doprava"),
    ("kočí", "kočí", "doprava"), ("povozník", "povozník", "doprava"), ("vozka", "kočí", "doprava"),
    ("kupec", "kupec", "obchod"), ("obchodník", "obchodník", "obchod"), ("hokynář", "hokynář", "obchod"),
    ("hostinsk", "hostinský", "úřad a služby"), ("šenkýř", "hostinský", "úřad a služby"), ("učitel", "učitel", "úřad a služby"),
    ("kantor", "učitel", "úřad a služby"), ("úředník", "úředník", "úřad a služby"), ("četník", "četník", "úřad a služby"),
    ("policajt", "policista", "úřad a služby"), ("strážník", "policista", "úřad a služby"), ("rychtář", "rychtář", "úřad a služby"),
    ("soudní sluha", "soudní sluha", "úřad a služby"), ("sluha", "sluha", "úřad a služby"), ("služka", "služka", "úřad a služby"),
    ("voják", "voják", "úřad a služby"), ("kaprál", "voják", "úřad a služby"), ("vysloužil", "voják", "úřad a služby"),
    ("havíř", "horník", "dělník"), ("horník", "horník", "dělník"), ("nádeník", "nádeník", "dělník"),
    ("tovární", "tovární dělník", "dělník"), ("dělník v továrně", "tovární dělník", "dělník"), ("dělník", "dělník", "dělník"),
    ("mistr", "mistr řemesla", "řemeslo"),   # „tkalcovský mistr“ dopadne jako tkadlec, „purkmistr“ se nepočítá (začátek slova)
]
POVOLANI_RE = [(re.compile(r"(?<!\w)" + re.escape(kw)), name, grp) for kw, name, grp in POVOLANI]


def parse_date(text):
    m = re.search(DATE, text)
    if not m:
        return None
    d, mq, mo, y = m.groups()
    try:
        return date(int(y), int(mq or mo), int(d)), bool(mq)
    except ValueError:
        return None


def when(facts, sign, y=""):
    """Datum narození (sign „*“) nebo úmrtí („†“) z faktů, jinak rok z faktu; z let y („1888–1889“, „* 1931“) jen bez faktu.
    Vrací (date nebo None, rok, přesné) nebo None. Nejisté údaje („† před 1840“, „po“, „mezi“, „asi 1761–1766“) se přeskočí."""
    fs = first(facts, sign)
    for f in fs:
        if re.match(r".\s*(?:asi\s+)?(?:před|po|mezi|\?|\[)", f) or re.search(r"\d{4}\s*[–-]\s*\d{4}", f[:30]):
            continue
        d = parse_date(f)
        if d:
            return d[0], d[0].year, not d[1]
        m = re.search(r"(?<!\d)(\d{4})(?!\d)", f)
        if m:
            return None, int(m.group(1)), False
    if fs:
        return None
    y = re.sub(r"\s*[–-]\s*", "–", (y or "").strip())
    if sign == "*" and not y.startswith(("†", "?", "žil", "po ", "před ", "mezi")):
        m = re.match(r"(?:\*\s*)?(?:asi\s+|kolem\s+|≈)?(\d{4})", y)
        if m:
            return None, int(m.group(1)), False
    if sign == "†":
        m = re.search(r"(?:–|†\s*)(?:asi\s+|≈)?(\d{4})(?!\d|\s*/|\s*\(?\?)", y)
        if m:
            return None, int(m.group(1)), False
    return None


def age_hint(facts):
    """Věk ze zápisu o úmrtí: „† 11. 5. 1768 (8 dní)“ → 0, „† 1873 Obec, 54 let, souchotiny“ → 54; jinak None."""
    for f in first(facts, "†"):
        m = re.search(r"(?<![\d.])(\d{1,3})\s*(?:let|roků|roky|rok)\b(?!\s+při)", f)
        if m:
            return int(m.group(1))
        if re.search(r"(?<![\d.])\d{1,2}\s*(?:dn|den|týd|měs|hod)", f):
            return 0
    return None


def life_age(b, d, facts):
    """Věk při úmrtí: (věk, přesný) z narození b a úmrtí d (výstupy when), nebo z věku v zápisu; jinak None."""
    if b and d and b[2] and d[2]:
        return age(b[0], d[0]), True
    h = age_hint(facts)
    if h is not None:
        return h, False
    if b and d and d[1] >= b[1]:
        return d[1] - b[1], False
    return None


def avg(vals):
    return round(sum(vals) / len(vals), 1) if vals else None


def stoleti(year):
    return f"{(year - 1) // 100 + 1}. století"


def first(facts, sign):
    return [f for f in facts if f.startswith(sign)]


def place_of(text):
    """„* 28. 7. 1870 Horní Lhota čp. 45“ (i „č. 45“, „č. p. 45“) → „Horní Lhota“."""
    m = re.search(DATE + r"\s+(.+)", text)
    if not m:
        return None
    rest = m.group(5)
    rest = re.split(r"\s+čp?\.|\s*\(|,|\s+–", rest)[0].strip()
    return rest or None


def age(a, b):
    return b.year - a.year - ((b.month, b.day) < (a.month, a.day))


def main():
    site = json.load(open(SITE, encoding="utf-8"))
    people = list(site["people"].values())
    anc = [p for p in people if p.get("k", 0) >= 1 and p.get("st") != "unk" and not p["name"].startswith(("otec ", "matka "))]
    bys = {p["slug"]: p for p in people}

    def ref(p, extra=None):
        r = {"slug": p["slug"], "name": p["name"], "years": p.get("years", "")}   # s "puvodni_jmena" v původním tvaru
        if extra is not None:
            r["val"] = extra
        return r

    born, died, byear = {}, {}, {}
    for p in anc:
        b = next((parse_date(f) for f in first(p["facts"], "*") if parse_date(f)), None)
        d = next((parse_date(f) for f in first(p["facts"], "†") if parse_date(f)), None)
        if b:
            born[p["slug"]] = b[0]
        if d:
            died[p["slug"]] = d[0]
        bw = when(p["facts"], "*", p.get("y"))
        if bw:
            byear[p["slug"]] = bw[1]
    sex_of = lambda p: p.get("sex") or ("M" if p["k"] % 2 == 0 else "F")

    # věk dožití (předci – všichni se dožili dospělosti, jinak by neměli děti); bez přesných dat přibližně
    life = []
    for p in anc:
        la = life_age(when(p["facts"], "*", p.get("y")), when(p["facts"], "†", p.get("y")), p["facts"])
        if la and 14 <= la[0] <= 110:
            r = ref(p, la[0])
            r["sex"], r["asi"], r["rok"] = sex_of(p), not la[1], byear.get(p["slug"])
            life.append(r)
    life.sort(key=lambda r: -r["val"])
    PASMA_ZIVOT = ["do 39", "40–49", "50–59", "60–69", "70–79", "80–89", "90 a víc"]
    pasmo_zivot = lambda v: PASMA_ZIVOT[min(max(v // 10 - 3, 0), 6)]

    # sňatky: věk a měsíc
    wed_age = {"M": [], "F": []}
    months = Counter()
    seen = set()
    for p in anc:
        sex = sex_of(p)
        for f in first(p["facts"], "×"):
            w = parse_date(f)
            wy = w[0].year if w else int(m.group(1)) if (m := re.match(r"×\s*(\d{4})\b", f)) else None
            if not wy:
                continue
            if w:
                key = (w[0], place_of(f))
                if key not in seen:
                    seen.add(key)
                    months[w[0].month] += 1
            a, asi = None, False
            if w and p["slug"] in born:
                a = age(born[p["slug"]], w[0])
            else:
                m = next((re.search(r"(\d+) let při sňatku", g) for g in p["facts"] if "let při sňatku" in g), None)
                if m:
                    a = int(m.group(1))
                elif p["slug"] in byear:
                    a, asi = wy - byear[p["slug"]], True
            if a is not None and 14 <= a <= 80:
                r = ref(p, a)
                r["asi"], r["rok"] = asi, wy
                wed_age[sex].append(r)
            break   # jen první (nejstarší zapsaný) sňatek
    PASMA_SNATEK = ["do 19", "20–24", "25–29", "30–34", "35–39", "40 a víc"]
    pasmo_snatek = lambda v: PASMA_SNATEK[min(max(v // 5 - 3, 0), 5)]

    # věkový rozdíl manželů (rodiče předka, oba se známým rokem narození): kladný = muž starší
    couple = []
    for p in anc:
        f, m = bys.get(p.get("father")), bys.get(p.get("mother"))
        if f and m and f["slug"] in byear and m["slug"] in byear and (f["slug"], m["slug"]) not in {(c["muz"]["slug"], c["zena"]["slug"]) for c in couple}:
            couple.append({"muz": ref(f), "zena": ref(m), "val": byear[m["slug"]] - byear[f["slug"]]})

    # věk otce a matky při narození dítěte (generační odstup)
    gap = {"M": [], "F": []}
    for p in anc:
        if p["slug"] not in born:
            continue
        for par, sex in (("father", "M"), ("mother", "F")):
            s = p.get(par)
            if s and s in born:
                gap[sex].append({"parent": ref(bys[s]), "child": ref(p), "val": age(born[s], born[p["slug"]])})

    # počet dětí a dětská úmrtnost: rodiny předků s dohledanými sourozenci ("sour": "hotovo")
    def child(name, sex, facts, y, text, ancestor, born_key=""):
        """Dítě rodiny; ancestor = slug předka (ten se dospělosti dožil), u sourozence None."""
        b, d = when(facts, "*", y), when(facts, "†", y)
        la = life_age(b, d, facts)
        hint = re.search(r"zemřel[a]?\s+(?:jako\s+|v\s+|krátce\s+|hned\s+)?(malý|malá|dítě|dětství|novorozen|kojen|po\s+narození)", text or "", re.I)
        osud = "prezil" if ancestor else None
        if not osud and la is not None:
            osud = "zemrel" if la[0] < 15 else "prezil"
        if not osud and hint:
            osud = "zemrel"
        if not osud and b:   # stopa dospělého života: sňatek, povolání, fakt nebo „po 1895“ aspoň 15 let po narození
            later = [int(x) for f in facts if not f.startswith(("*", "†")) for x in re.findall(r"(?<!\d)(1[5-9]\d\d|20\d\d)(?!\d)", f)]
            later += [int(x) for x in re.findall(r"po\s+(\d{4})", y or "")]
            if first(facts, "×") or any(v - b[1] >= 15 for v in later) or \
                    any(rx.search(f) for f in facts if not f.startswith(("*", "†")) for rx, _, _ in POVOLANI_RE):
                osud = "prezil"
        # do prvních narozenin: věk 0 (i rozdíl let 0 – narozen a zemřel týž rok), bez let „zemřel jako novorozenec“
        kojenec = osud == "zemrel" and (la[0] == 0 if la else not re.match(r"malý|malá|dítě|dětství", hint.group(1)))
        return {"name": name, "sex": sex, "rok": b[1] if b else None, "osud": osud or "nevime", "kojenec": kojenec,
                "vek": la[0] if la and osud == "zemrel" else None, "umrti": d[1] if d else None,
                "predek": ancestor, "born": born_key}

    fams = {}
    for p in people:
        if p.get("k", 0) < 1 or not p.get("family") or p["name"].startswith(("otec ", "matka ")):
            continue
        fam = fams.setdefault(p["family"], {"father": p.get("father"), "mother": p.get("mother"), "kids": [], "done": True, "jmena": set()})
        fam["done"] &= p.get("sibStatus") == "done"
        fam["kids"].append(child(p.get("modern") or p["name"], sex_of(p), p["facts"], p.get("y"), "", p["slug"], p.get("born") or ""))
        fam["jmena"].add((p.get("modern") or p["name"], (p.get("born") or "")[:4]))
        for e in p.get("side", []):
            rel = (e.get("rel") or "").strip().lower()
            if e.get("kind") != "sib":
                continue
            if rel not in ("bratr", "sestra"):   # „sourozenci“ za víc lidí – počet dětí neznáme
                fam["done"] = False
                continue
            fam.setdefault("sibs", []).append((e, "M" if rel == "bratr" else "F"))
    families_all = []
    for fid, fam in fams.items():
        for e, sex in fam.get("sibs", []):
            if (e["name"], (e.get("born") or "")[:4]) in fam["jmena"]:   # sourozenec, který je zároveň předkem
                continue
            fam["kids"].append(child(e["name"], sex, e.get("facts", []), e.get("years", ""), e.get("text", ""), None, e.get("born") or ""))
        roky = [c["rok"] for c in fam["kids"] if c["rok"]]
        families_all.append({"id": fid, "father": ref(bys[fam["father"]]) if fam["father"] in bys else None,
                             "mother": ref(bys[fam["mother"]]) if fam["mother"] in bys else None,
                             "kids": fam["kids"], "rok": min(roky) if roky else None, "done": fam["done"]})
    families_done = [f for f in families_all if f["done"]]
    kids_all = [c for f in families_done for c in f["kids"]]

    def umrtnost(kids):
        n = Counter(c["osud"] for c in kids)
        return {"deti": len(kids), "zemrelo": n["zemrel"], "kojenci": sum(c["kojenec"] for c in kids),
                "prezilo": n["prezil"], "nevime": n["nevime"]}

    cent_rows = defaultdict(list)
    for f in families_done:
        if f["rok"]:
            cent_rows[stoleti(f["rok"])].append(f)
    biggest = max(families_done, key=lambda f: len(f["kids"]), default=None)

    # povolání
    occ = defaultdict(list)
    groups = Counter()
    occ_cent = defaultdict(Counter)   # století narození → skupina povolání → počet
    for p in anc:
        found = []
        for f in p["facts"]:
            if f.startswith(("*", "†", "×")) or re.search(r"\bdcera\b|\bsyn\b", f):
                continue
            for rx, name, grp in POVOLANI_RE:
                if rx.search(f) and name not in [x[0] for x in found]:
                    found.append((name, grp))
                    break
        for name, grp in found:
            occ[(name, grp)].append(ref(p))
        if found:
            groups[found[0][1]] += 1
            if p["slug"] in byear:
                occ_cent[stoleti(byear[p["slug"]])][found[0][1]] += 1
    occ_list = sorted(({"name": n, "group": g, "people": v} for (n, g), v in occ.items()), key=lambda x: (-len(x["people"]), x["name"]))

    # jak daleko si brali: vzdálenost rodišť manželů (rodiče předka) podle souřadnic z data/mista.json
    mista = []
    if os.path.exists(MISTA):
        for nm, e in json.load(open(MISTA, encoding="utf-8")).items():
            if "lat" in e and not e.get("hypoteza"):
                mista.append((nm, re.compile(e.get("re") or re.escape(nm)), e["lat"], e["lon"]))

    def rodiste(p):
        """Místo z mista.json, které se ve faktu o narození objeví nejdřív (poznámky v závorce bývají až za ním)."""
        for f in first(p["facts"], "*"):
            hits = [(m.start(), nm, lat, lon) for nm, rx, lat, lon in mista if (m := rx.search(f))]
            if hits:
                return min(hits)[1:]
        return None

    def km(a, b):
        la1, lo1, la2, lo2 = map(math.radians, (a[1], a[2], b[1], b[2]))
        h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
        return 2 * 6371 * math.asin(math.sqrt(h))

    PASMA_KM = ["stejná obec", "do 5 km", "5–10 km", "10–20 km", "20–50 km", "přes 50 km"]
    pasmo_km = lambda v: PASMA_KM[0 if v < 0.5 else 1 if v < 5 else 2 if v < 10 else 3 if v < 20 else 4 if v < 50 else 5]
    pary, seen_par = [], set()
    for p in anc:
        f, m = bys.get(p.get("father")), bys.get(p.get("mother"))
        if not f or not m or (f["slug"], m["slug"]) in seen_par:
            continue
        seen_par.add((f["slug"], m["slug"]))
        a, b = rodiste(f), rodiste(m)
        if not a or not b:
            continue
        stem = (m.get("modern") or m["name"]).split()[-1][:4]
        wed = [x for x in first(f["facts"], "×") if stem in x] or first(f["facts"], "×") or first(m["facts"], "×")
        wy = int(y.group(1)) if wed and (y := re.search(r"(?<!\d)(\d{4})(?!\d)", wed[0])) else \
            byear[f["slug"]] + 27 if f["slug"] in byear else None
        d = 0.0 if a[0] == b[0] else km(a, b)
        pary.append({"muz": ref(f), "zena": ref(m), "odkud": a[0], "kam": b[0], "km": round(d, 1), "rok": wy})
    pary.sort(key=lambda x: -x["km"])
    km_cent = defaultdict(list)
    for x in pary:
        if x["rok"]:
            km_cent[stoleti(x["rok"])].append(x)

    # pořadí předka mezi sourozenci (jen rodiny s dohledanými sourozenci a známým pořadím narození všech dětí)
    poradi = []
    for f in families_done:
        kids = f["kids"]
        if any(not c["born"] for c in kids):
            continue
        kids = sorted(kids, key=lambda c: c["born"])
        for i, c in enumerate(kids):
            if not c["predek"]:
                continue
            same = [k for k in kids if k is not c and k["born"][:4] == c["born"][:4]]
            if any(len(k["born"]) < 10 or len(c["born"]) < 10 for k in same):   # týž rok bez data – pořadí nejisté
                continue
            sons = [k for k in kids if k["sex"] == c["sex"] and k["osud"] != "zemrel"]   # bratři/sestry, kteří nezemřeli jako malí
            poradi.append({**ref(bys[c["predek"]]), "sex": c["sex"], "pos": i + 1, "n": len(kids),
                           "pos_pohl": sons.index(c) + 1, "n_pohl": len(sons),
                           "deti": [{"sex": k["sex"], "osud": k["osud"], "predek": k is c} for k in kids]})

    def misto_v_rade(pos, n):
        return "jediné dítě" if n == 1 else "nejstarší" if pos == 1 else "nejmladší" if pos == n else "uprostřed"
    PORADI = ["nejstarší", "uprostřed", "nejmladší", "jediné dítě"]

    # místa narození
    places = Counter()
    for p in anc:
        for f in first(p["facts"], "*"):
            pl = place_of(f)
            if pl and parse_date(f):
                pl = re.sub(r"\s+\(.*", "", pl)
                places[pl] += 1
                break

    # křestní jména předků a jejich sourozenců (i nevlastních), celkem a podle století narození
    def given(name):
        fn = (name or "").split()[0] if (name or "").split() else ""
        return fn if fn[:1].isupper() and fn.rstrip(".").isalpha() and not fn.endswith(".") else None

    named = []   # (jméno, pohlaví, rok narození)
    for p in anc:
        named.append((given(p.get("modern") or p["name"]), sex_of(p), byear.get(p["slug"])))
    anc_names = {(p.get("modern") or p["name"], (p.get("born") or "")[:4]) for p in anc}
    for p in people:
        if p.get("k", 0) < 1:
            continue
        for e in p.get("side", []):
            rel = (e.get("rel") or "").lower()
            sx = "M" if "bratr" in rel else "F" if "sestra" in rel else None
            if not sx or rel.split()[0] in ("bratři", "sestry") or (e["name"], (e.get("born") or "")[:4]) in anc_names:
                continue
            b = when(e.get("facts", []), "*", e.get("years", ""))
            named.append((given(e["name"]), sx, b[1] if b else None))
    named = [x for x in named if x[0]]
    names = {sx: Counter(n for n, s2, _ in named if s2 == sx) for sx in "MF"}
    cents = Counter(stoleti(y) for _, _, y in named if y)
    cents = sorted((c for c, n in cents.items() if n >= 5), key=lambda c: int(c.split(".")[0]))
    names_cent = {"stoleti": cents,
                  "pocet": {sx: [sum(1 for _, s2, y in named if s2 == sx and y and stoleti(y) == c) for c in cents] for sx in "MF"}}
    for sx in "MF":
        top = [n for n, _ in names[sx].most_common(8)]
        names_cent[sx] = [{"name": n, "counts": [sum(1 for n2, s2, y in named if n2 == n and s2 == sx and y and stoleti(y) == c)
                                                 for c in cents]} for n in top]

    # jméno po sourozenci, který zemřel jako malý (další dítě téhož pohlaví dostalo stejné jméno)
    po_zemrelem = []
    for f in families_all:
        kids = sorted((c for c in f["kids"] if c["rok"]), key=lambda c: c["rok"])
        for i, a in enumerate(kids):
            if a["osud"] != "zemrel" or not given(a["name"]):
                continue
            b = next((c for c in kids[i + 1:] if c["sex"] == a["sex"] and given(c["name"]) == given(a["name"])
                      and c["rok"] >= (a["umrti"] or a["rok"])), None)
            if b:
                po_zemrelem.append({"name": given(a["name"]), "prvni": a["rok"], "vek": a["vek"], "kojenec": a["kojenec"],
                                    "druhy": b["rok"], "father": f["father"], "mother": f["mother"]})
    po_zemrelem.sort(key=lambda x: x["prvni"])

    # víra a církve
    faith = []
    for p in anc:
        for f in p["facts"]:
            if re.search(r"církv|vyznání|evangel|přestoupil|židovsk|izraelit", f, re.I):
                faith.append(ref(p, f))
    illeg = [ref(p) for p in anc if any(re.search(r"nemanželsk", f, re.I) for f in p["facts"] + [p.get("note") or ""])]
    legit = [ref(p) for p in anc if any(re.search(r"legitim", f, re.I) for f in p["facts"] + [p.get("note") or ""])]

    # zápisy
    recs = list(site["records"].values()) if isinstance(site["records"], dict) else site["records"]
    druh = Counter()
    arch = Counter()
    decades = Counter()
    for r in recs:
        dr = r.get("kind") or r.get("druh") or ""
        druh[{"N": "křty a narození", "O": "sňatky", "Z": "úmrtí"}.get(dr, "jiné")] += 1
        arch[r.get("portal") or "jiné"] += 1
        y = re.findall(r"\d{4}", r.get("datum") or r.get("date") or "")
        if y:
            decades[int(y[-1]) // 50 * 50] += 1

    gens = Counter(p.get("gen", 0) for p in anc)
    years_b = sorted(born.values())
    out = {
        "prehled": {
            "predku": len(anc),
            "dolozeno": sum(1 for p in anc if p.get("st") == "doc"),
            "generaci": max(gens) if gens else 0,
            "zapisu": len(recs),
            "nejstarsi_narozeni": years_b[0].year if years_b else None,
            "prijmeni": len({(p.get("modern") or p["name"]).split()[-1].replace("ová", "") for p in anc}),
            "mist": len(places),
        },
        "generace": [{"gen": g, "pocet": gens[g], "max": 2 ** g} for g in sorted(gens)],
        "povolani": occ_list,
        "povolani_skupiny": [{"name": k, "count": v} for k, v in groups.most_common()],
        "povolani_stoleti": [{"name": c, "pocet": sum(occ_cent[c].values()), "skupiny": [{"name": g, "count": occ_cent[c][g]} for g, _ in groups.most_common()]}
                             for c in sorted(occ_cent, key=lambda c: int(c.split(".")[0])) if sum(occ_cent[c].values()) >= 3],
        "mista": [{"name": k, "count": v} for k, v in places.most_common(15)],
        "doziti": {"list": life, "prumer": avg([r["val"] for r in life]),
                   **{sx: {"prumer": avg([r["val"] for r in life if r["sex"] == sx]), "pocet": sum(r["sex"] == sx for r in life)} for sx in "MF"},
                   "pasma": [{"name": b, **{sx: sum(r["sex"] == sx and pasmo_zivot(r["val"]) == b for r in life) for sx in "MF"}} for b in PASMA_ZIVOT],
                   "stoleti": [{"name": c, **{sx: avg([r["val"] for r in life if r["sex"] == sx and r["rok"] and stoleti(r["rok"]) == c]) for sx in "MF"},
                                "pocet": sum(1 for r in life if r["rok"] and stoleti(r["rok"]) == c)}
                               for c in sorted({stoleti(r["rok"]) for r in life if r["rok"]}, key=lambda c: int(c.split(".")[0]))]},
        "snatek_vek": {s: {"list": sorted(v, key=lambda r: r["val"]), "prumer": avg([r["val"] for r in v])} for s, v in wed_age.items()},
        "snatek_pasma": [{"name": b, **{sx: sum(pasmo_snatek(r["val"]) == b for r in wed_age[sx]) for sx in "MF"}} for b in PASMA_SNATEK],
        "snatek_stoleti": [{"name": c, **{sx: avg([r["val"] for r in wed_age[sx] if stoleti(r["rok"]) == c]) for sx in "MF"},
                            "pocet": sum(stoleti(r["rok"]) == c for sx in "MF" for r in wed_age[sx])}
                           for c in sorted({stoleti(r["rok"]) for sx in "MF" for r in wed_age[sx]}, key=lambda c: int(c.split(".")[0]))],
        "manzele_rozdil": {"prumer": avg([c["val"] for c in couple]), "pocet": len(couple),
                           "muz_starsi": sum(c["val"] > 0 for c in couple), "zena_starsi": sum(c["val"] < 0 for c in couple),
                           "stejne": sum(c["val"] == 0 for c in couple),
                           "nejvetsi": max(couple, key=lambda c: abs(c["val"])) if couple else None},
        "deti": {"rodin": len(families_done), "prumer": avg([len(f["kids"]) for f in families_done]),
                 "nejvic": {"father": biggest["father"], "mother": biggest["mother"], "pocet": len(biggest["kids"])} if biggest else None,
                 "rozdeleni": [{"name": str(n), "count": sum(len(f["kids"]) == n for f in families_done)}
                               for n in range(1, max((len(f["kids"]) for f in families_done), default=0) + 1)],
                 **umrtnost(kids_all),
                 "stoleti": [{"name": c, "rodin": len(fs), "prumer": avg([len(f["kids"]) for f in fs]), **umrtnost([k for f in fs for k in f["kids"]])}
                             for c, fs in sorted(cent_rows.items(), key=lambda x: int(x[0].split(".")[0]))],
                 "zemreli": sorted(({"name": c["name"], "rok": c["rok"], "vek": c["vek"], "kojenec": c["kojenec"],
                                     "father": f["father"], "mother": f["mother"]}
                                    for f in families_done for c in f["kids"] if c["osud"] == "zemrel"), key=lambda x: x["rok"] or 9999)},
        "snatek_mesice": [{"name": MESICE[m - 1], "count": months.get(m, 0)} for m in range(1, 13)],
        "rodice_vek": {s: {"prumer": round(sum(x["val"] for x in v) / len(v), 1) if v else None,
                           "nejmladsi": min(v, key=lambda x: x["val"]) if v else None,
                           "nejstarsi": max(v, key=lambda x: x["val"]) if v else None, "pocet": len(v)} for s, v in gap.items()},
        "jmena": {s: [{"name": k, "count": v} for k, v in c.most_common(10)] for s, c in names.items()},
        "jmena_pocet": {s: sum(c.values()) for s, c in names.items()},
        "snatek_km": {"pocet": len(pary), "median": sorted(x["km"] for x in pary)[len(pary) // 2] if pary else None,
                      "pasma": [{"name": b, "count": sum(pasmo_km(x["km"]) == b for x in pary)} for b in PASMA_KM],
                      "stoleti": [{"name": c, "pocet": len(v), "stejna": sum(x["km"] < 0.5 for x in v),
                                   "do10": sum(x["km"] < 10 for x in v), "prumer": avg([x["km"] for x in v])}
                                  for c, v in sorted(km_cent.items(), key=lambda x: int(x[0].split(".")[0]))],
                      "nejdal": pary[:5]},
        "poradi": {"list": sorted(poradi, key=lambda x: bys[x["slug"]]["k"]),
                   **{sx: [{"name": k, "count": sum(misto_v_rade(x["pos"], x["n"]) == k for x in poradi if x["sex"] == sx)} for k in PORADI] for sx in "MF"},
                   "syn": [{"name": k, "count": sum(misto_v_rade(x["pos_pohl"], x["n_pohl"]) == k for x in poradi if x["sex"] == "M")} for k in PORADI]},
        "jmena_stoleti": names_cent,
        "jmeno_po_zemrelem": po_zemrelem,
        "vira": faith,
        "nemanzelske": illeg,
        "legitimace": legit,
        "zapisy_druh": [{"name": k, "count": v} for k, v in druh.most_common()],
        "zapisy_portal": [{"name": k, "count": v} for k, v in arch.most_common()],
        "zapisy_obdobi": [{"name": f"{d}–{d + 49}", "count": decades[d]} for d in sorted(decades)],
    }
    json.dump(out, open(OUT, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(f"statistiky: {len(anc)} předků, {len(life)} s věkem dožití, {sum(len(v) for v in wed_age.values())} s věkem při sňatku, "
          f"{len(occ_list)} povolání, {len(families_done)} rodin s dohledanými sourozenci ({len(kids_all)} dětí)")


if __name__ == "__main__":
    main()
