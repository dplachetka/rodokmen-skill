#!/usr/bin/env python3
"""Časová osa rodů pro web: čte web/src/data/site.json a zapíše web/src/data/osa.json. Volá ho tools/export_web.py
na konci exportu; jde spustit i samostatně.

Pro každý rod (čísla 8–15) jedna linie: od výchozí osoby přes zakladatele rodu dál po otcích, v každém řádku pár
(muž a jeho žena). Roky z faktů jako ve statistikách (statistiky.when); co chybí, se odhadne a na webu je čárkovaně:
narození podle sňatku nebo narození dítěte, úmrtí „† před 1840“ / „žil 1851“ jako mez, žijící do dneška.
"""
import json, os, re, sys
from datetime import date

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
from statistiky import first, when   # stejné čtení dat jako statistiky

ROOT = os.path.dirname(TOOLS)
SITE = os.path.join(ROOT, "web", "src", "data", "site.json")
OUT = os.path.join(ROOT, "web", "src", "data", "osa.json")
DNES = date.today().year
ASI = re.compile(r"(?:^|\s)(?:asi|kolem|cca)\s|≈")


def marriage(m, f):
    """Rok sňatku páru: fakt muže se jménem ženy, jinak první sňatek muže nebo ženy."""
    stem = (f.get("modern") or f["name"]).split()[-1][:4] if f else ""
    wed = [x for x in first(m["facts"], "×") if stem and stem in x] if m else []
    for x in wed + (first(m["facts"], "×") if m else []) + (first(f["facts"], "×") if f else []):
        x = re.sub(r"\([^)]*\)", "", x)   # „× Kateřina (* asi 1621)“ – rok v závorce není rok sňatku
        if not re.match(r"×\s*(?:\(?\d\)\s*)?(?:asi\s+)?(?:před|po|mezi|\?)", x) and (y := re.search(r"(?<!\d)(\d{4})(?!\d)", x)):
            return int(y.group(1))
    return None


def life(p, wed, child_born, man):
    """{slug, name, b, d, fb, fd}: fb '' známé, 'a' asi, '?' odhad; fd navíc 'p' před, 'o' ještě žil, 'z' žije."""
    b = when(p["facts"], "*", p.get("y"))
    bt = " ".join(first(p["facts"], "*")) or p.get("y") or ""
    if b:
        by, fb = b[1], "a" if ASI.search(bt) else ""
    elif wed:
        by, fb = wed - (27 if man else 23), "?"
    elif child_born:
        by, fb = child_born - 30, "?"
    else:
        return None
    d = when(p["facts"], "†", p.get("y"))
    dt = " ".join(first(p["facts"], "†"))
    y = p.get("y") or ""
    if d:
        dy, fd = d[1], "a" if ASI.search(dt) else ""
    elif m := re.search(r"před\s+(?:\d{1,2}[./]\s*)*(\d{4})", dt or y):
        dy, fd = int(m.group(1)), "p"
    elif m := re.search(r"(?:\bpo|žil)\s+(?:\d{1,2}[./]\s*)*(\d{4})", dt or y):
        dy, fd = int(m.group(1)), "o"
    elif not dt and "†" not in y and by > DNES - 100:
        dy, fd = DNES, "z"
    else:
        dy, fd = min(DNES, max(by + 60, (wed or by) + 25)), "?"
    if dy < by:
        dy = by
    return {"slug": p["slug"], "name": p["name"], "b": by, "d": dy, "fb": fb, "fd": fd}


def main():
    site = json.load(open(SITE, encoding="utf-8"))
    people = site["people"]
    byk = {p["k"]: p for p in people.values() if not p["name"].startswith(("otec ", "matka "))}
    rody = []
    for line in sorted(site["lines"].values(), key=lambda l: l["k"]):
        k = line["k"]
        down = []
        c = k
        while c >= 1:
            down.append(c)
            c //= 2
        up = []
        c = 2 * k
        while c in byk:
            up.append(c)
            c *= 2
        chain = list(reversed(up)) + down   # od nejstaršího po výchozí osobu
        rows = []
        for i, kk in enumerate(chain):
            if kk not in byk:
                continue
            if kk == 1:
                m, f = (byk[1], None) if byk[1].get("sex", "M") == "M" else (None, byk[1])
            else:
                m, f = byk.get(kk & ~1), byk.get(kk | 1)
            wed = marriage(m, f) if m and f else None
            nxt = byk.get(chain[i + 1]) if i + 1 < len(chain) else None
            nb = when(nxt["facts"], "*", nxt.get("y")) if nxt else None
            row = {"gen": byk[kk]["gen"], "k": kk, "svatba": wed,
                   "m": life(m, wed, nb and nb[1], True) if m else None,
                   "f": life(f, wed, nb and nb[1], False) if f else None}
            if row["m"] or row["f"]:
                rows.append(row)
        if rows:
            rody.append({"slug": line["slug"], "name": line["name"], "k": k, "color": line["color"], "rows": rows})
    json.dump({"dnes": DNES, "rody": rody}, open(OUT, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(f"časová osa: {len(rody)} rodů, {sum(len(r['rows']) for r in rody)} řádků")


if __name__ == "__main__":
    main()
