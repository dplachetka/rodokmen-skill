#!/usr/bin/env python3
"""Celý rodokmen jako JEDEN soubor HTML ke sdílení (e-mail, flash, WhatsApp) – bez serveru a bez internetu.

Obsah je stejný jako na webu (data z export_web.build_site): úvod, příběh rodu, vějíř předků, předci po generacích,
rody a hypotézy, mapa (bez internetu – obrys Česka a obce), zajímavosti, co hledáme, všechny zápisy s výřezem,
přepisem a překladem, rodinné dokumenty, výzkumný deník; u každého předka údaje, rodina, sourozenci a lidé kolem
rodiny. Obrázky jsou vložené přímo do souboru (zmenšené).

Vytvoří dva soubory (do složky vystupy/, nebo kam řeknete):
  rodokmen.html         s JavaScriptem: navíc hledání, přibližování vějíře, stromový graf, filtr zápisů;
                        bez JavaScriptu funguje taky (panely přes #kotvy)
  rodokmen-bez-js.html  bez jediného skriptu – pro náhledy příloh (iPhone Mail/Soubory/WhatsApp, Android) a poštu,
                        která soubory se skripty blokuje
Použití: python3 -I tools/jeden_soubor.py [složka] [--jen-js | --jen-bez-js] [--sirka 1000] [--kvalita 50]
                                          [--bez-obrazku] [--bez-deniku]
Soubor NEMÁ přihlášení jako web – kdo ho dostane, vidí všechno. Sdílet jen se souhlasem (reference/soukromi.md);
nástroj před vytvořením vypíše upozornění ŽIJÍCÍ? a CITLIVÉ z kontrola.py.
Nástroj vznikl ve výzkumném projektu jednoho z uživatelů skillu.
"""
import base64, datetime, glob, hashlib, html, json, math, os, re, shutil, subprocess, sys, tempfile
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)   # python3 -I složku skriptu do sys.path nepřidá
import export_web as W      # build_site: stejná data jako web

ROOT, DATA = W.ROOT, W.DATA
WEBSRC = os.path.join(ROOT, "web", "src")

args = sys.argv[1:]


def opt(name, default):
    if name in args:
        i = args.index(name)
        val = args[i + 1]
        del args[i:i + 2]
        return val
    return default


SIRKA, KVALITA = int(opt("--sirka", 1000)), int(opt("--kvalita", 50))   # delší strana obrázku; barevné skeny jsou těžké
BEZ_OBR, BEZ_DENIKU = "--bez-obrazku" in args, "--bez-deniku" in args
VERZE = [v for v, f in ((True, "--jen-js"), (False, "--jen-bez-js")) if f in args] or [True, False]
args = [a for a in args if not a.startswith("--")]
OUT = os.path.abspath(args[0]) if args else os.path.join(ROOT, "vystupy")

e = lambda s: html.escape(str(s if s is not None else ""))


# ---------- soukromí: soubor nemá přihlášení, upozornění z kontrola.py ----------
def upozorneni():
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(TOOLS, "kontrola.py")], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    vazne = [l for l in r.stdout.splitlines() if "ŽIJÍCÍ?" in l or "CITLIVÉ" in l]
    print("POZOR: soubor nemá přihlášení jako web – kdo ho dostane, uvidí všechno. Sdílejte ho jen se souhlasem rodiny.")
    if vazne:
        print(f"Kontrola hlásí {len(vazne)} věcí, které by v souboru být neměly (vyřešte je, než ho pošlete dál):")
        for l in vazne:
            print("  " + l.replace("upozornění: ", "")[:220])


# ---------- obrázky: zmenšené a vložené jako data: URI ----------
MAGICK = shutil.which("magick") or next(iter(sorted(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))), None)
TMP = tempfile.mkdtemp(prefix="jeden-")
_obr = {}


def obrazek(klic):
    if BEZ_OBR or not klic:
        return ""
    if klic in _obr:
        return _obr[klic]
    src = os.path.join(ROOT, "vyrezy", klic + ".jpg")
    if not os.path.exists(src):
        _obr[klic] = ""
        return ""
    dst = os.path.join(TMP, hashlib.sha1(klic.encode()).hexdigest() + ".jpg")
    subprocess.run([MAGICK, src, "-auto-orient", "-resize", f"{SIRKA}x{SIRKA}>", "-strip", "-interlace", "JPEG",
                    "-sampling-factor", "4:2:0", "-quality", str(KVALITA), dst], check=True)
    _obr[klic] = "data:image/jpeg;base64," + base64.b64encode(open(dst, "rb").read()).decode()
    return _obr[klic]


# ---------- data webu ----------
cfg = W.jload("web.json", {})
site, texts, extra = W.build_site(cfg)
people, families, lines, places = site["people"], site["families"], site["lines"], site["places"]
recs = {r["key"]: r for r in site["records"]}
conf = site["config"]
slug_k = extra["slugs"]                       # Kekulé (i předek vícekrát) → adresa osoby
line_by_k = {l["k"]: l for l in lines.values()}
root = people[site["root"]]

A = dict(o=lambda s: "o-" + s, z=lambda k: "z-" + k, r=lambda f: "r-" + f, rod=lambda s: "rod-" + s, m=lambda i: f"m-{i}",
         d=lambda i: "d-" + i)
SEKCE = {"/": "uvod", "/pribehy/": "pribeh", "/vejir/": "vejir", "/strom/": "strom", "/predci/": "predci", "/rody/": "rody",
         "/mapa/": "mapa", "/zajimavosti/": "zajimavosti", "/hledame/": "hledame", "/zapisy/": "zapisy", "/denik/": "denik",
         "/hledat/": "vejir"}


def odkaz(url):
    """Adresa z textu webu → kotva v souboru (nebo vnější odkaz); None = jen text."""
    m = re.match(r"^/(osoba|zdroj|rod|rodina)/([^/#?]+)/?$", url)
    if m:
        kind, x = m.groups()
        if kind == "osoba" and x in people:
            return "#" + A["o"](x)
        if kind == "zdroj" and x in recs:
            return "#" + A["z"](x)
        if kind == "rod" and x in lines:
            return "#" + A["rod"](x)
        if kind == "rodina" and x in families:
            return "#" + A["r"](x)
        return None
    if url in SEKCE:
        return "#" + SEKCE[url]
    if re.match(r"^(https?:|mailto:)", url):
        return url
    return None


def inline(t):
    t = e(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)

    def a(m):
        cil = odkaz(html.unescape(m.group(2)))
        if not cil:
            return m.group(1)
        ven = ' target="_blank" rel="noopener"' if cil.startswith("http") else ""
        return f'<a href="{e(cil)}"{ven}>{m.group(1)}</a>'
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", a, t)


def md(text, h=3):
    """Markdown z data/ (nadpisy, odstavce, seznamy, tabulky, citace) → HTML; ## = h{h}."""
    text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    out = []
    for blok in re.split(r"\n\s*\n", text.strip()):
        radky = [r for r in blok.split("\n") if r.strip()]
        if not radky:
            continue
        if radky[0].startswith("#"):
            m = re.match(r"^(#+)\s*(.*)", radky[0])
            if len(m.group(1)) > 1:
                out.append(f"<h{min(6, h + len(m.group(1)) - 2)}>{inline(m.group(2))}</h{min(6, h + len(m.group(1)) - 2)}>")
            radky = radky[1:]
            if not radky:
                continue
        if all(r.lstrip().startswith("|") for r in radky):
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in radky]
            rows = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c) for c in r if c)]
            head, body = rows[0], rows[1:]
            out.append('<div class="tbox"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table></div>")
        elif re.match(r"^\s*([-*]|\d+\.)\s", radky[0]):
            tag = "ol" if re.match(r"^\s*\d+\.", radky[0]) else "ul"
            items = []
            for r in radky:
                if re.match(r"^\s*([-*]|\d+\.)\s", r):
                    items.append(re.sub(r"^\s*([-*]|\d+\.)\s+", "", r))
                elif items:
                    items[-1] += " " + r.strip()
            out.append(f"<{tag}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{tag}>")
        elif radky[0].startswith(">"):
            out.append("<blockquote>" + inline(" ".join(r.lstrip("> ") for r in radky)) + "</blockquote>")
        else:
            out.append(f"<p>{inline(' '.join(r.strip() for r in radky))}</p>")
    return "\n".join(out)


def frontmatter(text, key):
    m = re.search(rf"^{key}:\s*(.+)$", re.match(r"\A---\n(.*?)\n---\n", text or "", re.S).group(1), re.M) \
        if re.match(r"\A---\n.*?\n---\n", text or "", re.S) else None
    return m.group(1).strip().strip("'\"") if m else ""


# ---------- kousky HTML ----------
ST_CLASS = {"doc": "st-doc", "prob": "st-prob", "fam": "st-fam", "mh": "st-mh"}
SIDE_TITLE = {"sib": "Sourozenci", "kin": "Další příbuzní", "non": "Lidé kolem rodiny", "unknown": "Vztah zatím neuveden"}
CLOSE = '<div class="bar"><a class="btn close" href="#_" aria-label="Zavřít">✕ Zavřít</a></div>'


def side_groups(side):
    g = [("sib", [s for s in side if s["kind"] == "sib"]),
         ("kin", [s for s in side if s["kind"] in ("spouse", "child", "kin")]),
         ("non", [s for s in side if s["kind"] == "non"]),
         ("unknown", [s for s in side if s["kind"] not in ("sib", "spouse", "child", "kin", "non")])]
    return [(k, v) for k, v in g if v]


def plink(slug, roky=True):
    p = people.get(slug)
    if not p:
        return ""
    return f'<a href="#{A["o"](slug)}">{e(p["name"])}</a>' + (f' <span class="muted">{e(p["years"])}</span>' if roky and p["years"] else "")


def chip(text, cls=""):
    return f'<span class="chip {cls}">{e(text)}</span>' if text else ""


def reclink(key):
    r = recs[key]
    return (f'<a class="reclink" href="#{A["z"](key)}" data-r="{e(key)}">{e(r["title"])}'
            f'<span>{e(" · ".join(x for x in (r["kindName"], r["date"]) if x))}</span></a>')


def side_card(s):
    zap = "".join(reclink(r) for r in s["records"] if r in recs)
    return ('<div class="card">' + f'<h4>{e(s["name"])}{e(" (" + s["years"] + ")") if s["years"] else ""}</h4>'
            + ('<div class="chips">' + chip(s["rel"]) + chip(s["status"], ST_CLASS.get(s["st"], "st-unk")) + "</div>" if s["rel"] or s["status"] else "")
            + ("<ul class=facts>" + "".join(f"<li>{e(f)}</li>" for f in s["facts"]) + "</ul>" if s["facts"] else "")
            + (f'<p class="small">{e(s["text"])}</p>' if s["text"] else "") + (f'<div class="recs">{zap}</div>' if zap else "") + "</div>")


def rec_body(key):
    r = recs[key]
    boxes = "".join(f'<span class="bx" style="left:{b[0] * 100:.1f}%;top:{b[1] * 100:.1f}%;'
                    f'width:{(b[2] - b[0]) * 100:.1f}%;height:{(b[3] - b[1]) * 100:.1f}%"></span>' for b in r["boxes"])
    src = obrazek(key) if r["img"] else ""
    img = f'<div class="imgwrap"><img loading="lazy" src="{src}" alt="{e(r["title"])}">{boxes}</div>' if src else ""
    zdroj = e(" · ".join(x for x in (r["archive"], r["volume"]) if x)) + (f", snímek {e(r['scan'])}" if r["scan"] else "")
    url = r["url"] if re.match(r"^https?://", r["url"] or "") else ""
    if url:
        zdroj += f' · <a href="{e(url)}" target="_blank" rel="noopener">otevřít v archivu ({e(r["portal"])})</a>'
    return (f'<div class="recbody"><h4>{e(r["title"])}</h4><div class="meta">{e(" · ".join(x for x in (r["kindName"], r["date"]) if x))}</div>'
            f'{img}' + (f"<p>{e(r['summary'])}</p>" if r["summary"] else "")
            + (f"<details><summary>Překlad do češtiny</summary><pre>{e(r['cs'])}</pre></details>" if r["cs"] else "")
            + (f"<details><summary>Přepis originálu</summary><pre>{e(r['orig'])}</pre></details>" if r["orig"] else "")
            + f'<div class="meta">{zdroj}</div></div>')


def person_sheet(slug, js):
    p = people[slug]
    l = line_by_k.get(p["line"])
    nav = []
    if p["father"]:
        nav.append(f'<a class="btn" href="#{A["o"](p["father"])}">Otec: {e(people[p["father"]]["name"])}</a>')
    elif p["fatherUnknown"]:
        nav.append('<span class="btn off">Otec neuveden (nemanželské dítě)</span>')
    if p["mother"]:
        nav.append(f'<a class="btn" href="#{A["o"](p["mother"])}">Matka: {e(people[p["mother"]]["name"])}</a>')
    for c in p["children"]:
        nav.append(f'<a class="btn" href="#{A["o"](c)}">{"Syn" if people[c]["sex"] == "M" else "Dcera"}: {e(people[c]["name"])}</a>')
    if p["spouse"]:
        nav.append(f'<a class="btn" href="#{A["o"](p["spouse"])}">{"Manželka" if p["sex"] == "M" else "Manžel"}: {e(people[p["spouse"]]["name"])}</a>')
    if p["family"]:
        nav.append(f'<a class="btn" href="#{A["r"](p["family"])}">Rodina, ze které pochází</a>')
    if p["ownFamily"]:
        nav.append(f'<a class="btn" href="#{A["r"](p["ownFamily"])}">Jejich rodina</a>')
    if js:
        nav.append(f'<a class="btn jsonly" href="#strom" data-strom="{p["k"]}">Stromový graf od této osoby</a>')
    also = ""
    if p["also"]:
        pres = " i přes ".join(plink(c, False) for c in p["children"])
        also = f'<p class="note">V rodokmenu dvakrát – je předkem přes {pres}. Podruhé jako {e(", ".join(a["rel"] for a in p["also"]))}.</p>'
    side = "".join(f'<h3>{SIDE_TITLE[g]}</h3><div class="cards">{"".join(side_card(s) for s in lst)}</div>' for g, lst in side_groups(p["side"]))
    docs = "".join(f'<a class="reclink" href="#{A["d"](d["img"])}">{e(d["caption"])}</a>' for d in p["docs"])
    return (f'<section class="sheet" id="{A["o"](slug)}">{CLOSE}<div class="stripe" style="background:{l["color"] if l else "#C9B9A3"}"></div>'
            f'<h2 class="pn">{e(p["name"])}</h2><div class="py">{e(" · ".join(x for x in (p["years"], p["rel"]) if x))}</div>'
            f'<div class="chips">{chip(p["status"], ST_CLASS.get(p["st"], "st-unk"))}'
            + (f'<a class="chip" href="#{A["rod"](l["slug"])}"><i class="dot" style="background:{l["color"]}"></i>rod {e(l["name"])}</a>' if l else "")
            + f'</div><div class="nav">{"".join(nav)}</div>{also}'
            + ("<ul class=facts>" + "".join(f"<li>{e(f)}</li>" for f in p["facts"]) + "</ul>" if p["facts"] else "")
            + (f'<div class="note">{e(p["note"])}</div>' if p["note"] else "") + side
            + ("<h3>Zápisy z archivů</h3><div class=recs>" + "".join(reclink(r) for r in p["records"] if r in recs) + "</div>" if p["records"] else "")
            + (f"<h3>Rodinné dokumenty</h3><div class=recs>{docs}</div>" if docs else "") + "</section>")


def family_sheet(fid):
    f = families[fid]
    rodice = []
    for s, label in ((f["father"], "otec"), (f["mother"], "matka")):
        if s:
            rodice.append(f'<div class="card"><h4>{plink(s)}</h4><p class="small muted">{e(people[s]["rel"])}</p></div>')
        else:
            rodice.append(f'<div class="card"><p class="muted">{"V zápisech neuveden – dítě se narodilo jako nemanželské." if label == "otec" and f["fatherUnknown"] else "Zatím neznámá osoba."}</p></div>')
    groups = side_groups(f["side"])
    sibs = next((lst for g, lst in groups if g == "sib"), [])
    kids = [dict(p=people[c], born=people[c].get("born", "")) for c in f["children"]] + [dict(s=s, born=s.get("born", "")) for s in sibs]
    kids.sort(key=lambda x: (x["born"] == "", x["born"]))
    deti = ""
    for x in kids:
        if "s" in x:
            deti += side_card(x["s"])
            continue
        zivot = [t for t in x["p"]["facts"] if t.strip().startswith(("*", "†"))]
        deti += (f'<div class="card direct"><h4>{plink(x["p"]["slug"])}</h4><div class="chips">{chip("přímý předek – " + x["p"]["rel"])}</div>'
                 + ("<ul class=facts>" + "".join(f"<li>{e(t)}</li>" for t in zivot) + "</ul>" if zivot else "") + "</div>")
    sour = {"done": "Sourozence jsme dohledali všechny.", "partial": "Sourozence jsme hledali jen částečně – tady jsou ti, které jsme zatím našli."}.get(
        people[f["child"]].get("sibStatus"), "Další sourozence zatím systematicky nehledáme – tady jsou jen ti, na které jsme narazili.")
    jine = "".join(f'<h3>{SIDE_TITLE[g]}</h3><div class="cards">{"".join(side_card(s) for s in lst)}</div>' for g, lst in groups if g != "sib")
    title = " a ".join([people[f["father"]]["name"] if f["father"] else ("otec neuveden" if f["fatherUnknown"] else "neznámý otec"),
                        people[f["mother"]]["name"] if f["mother"] else "neznámá matka"])
    return (f'<section class="sheet" id="{A["r"](fid)}">{CLOSE}<h2 class="pn">Rodina: {e(title)}</h2>'
            f'<h3>Rodiče</h3><div class="cards">{"".join(rodice)}</div>'
            + ("<h3>Sňatek</h3><ul class=facts>" + "".join("<li>" + e(re.sub(r"^×\s*", "", m)) + "</li>" for m in f["marriage"]) + "</ul>" if f["marriage"] else "")
            + f'<h3>Děti</h3><div class="cards">{deti}</div><p class="small muted">{e(sour)}</p>{jine}'
            + ("<h3>Zápisy</h3><div class=recs>" + "".join(reclink(r) for r in f["records"] if r in recs) + "</div>" if f["records"] else "")
            + "</section>")


def record_sheet(key):
    r = recs[key]
    lidi = "".join(f'<a class="btn" href="#{A["o"](s)}">{e(people[s]["name"])}</a>' for s in r["people"] if s in people)
    return (f'<section class="sheet" id="{A["z"](key)}">{CLOSE}{rec_body(key)}'
            + (f"<h3>Kdo je v zápisu</h3><div class=nav>{lidi}</div>" if lidi else "") + "</section>")


def barva(k):
    return line_by_k[k]["color"] if k in line_by_k else "#C9B9A3"


def place_sheet(i, pl):
    rody = ""
    for g in pl["lines"]:
        nazev = "rod " + line_by_k[g["k"]]["name"] if g["k"] in line_by_k else "mimo rody"
        lidi = "".join('<a class="btn" href="#' + A["o"](s) + '">' + e(people[s]["name"]) + "</a>" for s in g["people"] if s in people)
        rody += f'<h3><i class="dot" style="background:{barva(g["k"])}"></i>{e(nazev)}</h3><div class="nav">{lidi}</div>'

    roky = f'{pl["years"][0]}–{pl["years"][1]}' if pl["years"] else ""
    return (f'<section class="sheet" id="{A["m"](i)}">{CLOSE}<h2 class="pn">{e(pl["name"])}</h2>'
            + (f'<div class="py">předci tu žili v letech {e(roky)}</div>' if roky else "")
            + ('<p class="note">Hypotéza – odsud rod možná pochází, zatím bez dokladu.</p>' if pl["hypothesis"] else "") + rody + "</section>")


# ---------- mapa bez internetu: přibližný obrys Česka a tečky obcí ----------
CESKO = [(12.09, 50.25), (12.20, 50.32), (12.32, 50.18), (12.50, 50.35), (12.95, 50.40), (13.25, 50.58), (13.55, 50.71), (13.90, 50.79),
         (14.30, 50.88), (14.38, 51.04), (14.62, 50.92), (14.82, 51.00), (15.02, 51.02), (15.00, 50.87), (15.38, 50.78), (15.80, 50.74),
         (16.10, 50.66), (16.33, 50.66), (16.44, 50.58), (16.20, 50.43), (16.35, 50.40), (16.55, 50.22), (16.70, 50.10), (16.90, 50.44),
         (17.20, 50.37), (17.70, 50.32), (17.75, 50.22), (18.05, 50.06), (18.35, 49.95), (18.58, 49.92), (18.85, 49.52), (18.55, 49.48),
         (18.40, 49.32), (18.12, 49.08), (17.92, 49.00), (17.65, 48.86), (17.20, 48.87), (16.95, 48.62), (16.54, 48.80), (16.10, 48.75),
         (15.75, 48.86), (15.28, 48.98), (15.00, 49.01), (14.95, 48.78), (14.72, 48.60), (14.40, 48.60), (14.05, 48.60), (13.83, 48.77),
         (13.50, 48.95), (13.17, 49.15), (12.90, 49.34), (12.65, 49.43), (12.50, 49.70), (12.40, 49.75), (12.47, 49.98), (12.20, 50.10)]


def mapa():
    if not places:
        return ""
    # výřez podle obcí (s okrajem), aby byly na telefonu čitelné; obrys Česka je jen pro orientaci a ořízne se
    lon = [p["lon"] for p in places]
    lat = [p["lat"] for p in places]
    dlo, dla = max(0.5, (max(lon) - min(lon)) * 0.15), max(0.3, (max(lat) - min(lat)) * 0.15)
    lo0, lo1, la0, la1 = min(lon) - dlo, max(lon) + dlo, min(lat) - dla, max(lat) + dla
    kx = math.cos(math.radians((la0 + la1) / 2))
    if (la1 - la0) < (lo1 - lo0) * kx * 0.45:          # příliš nízký pruh – dorovnat výšku
        d = ((lo1 - lo0) * kx * 0.45 - (la1 - la0)) / 2
        la0, la1 = la0 - d, la1 + d
    Wd = 600
    sc = Wd / ((lo1 - lo0) * kx)
    Hd = round((la1 - la0) * sc)
    P = lambda lo, la: (round((lo - lo0) * kx * sc, 1), round((la1 - la) * sc, 1))
    obrys = " ".join(f"{x},{y}" for x, y in (P(*c) for c in CESKO))
    tecky, popisky, obsazeno = [], [], []
    for pl in places:                                   # tečky jsou překážky pro popisky
        x, y = P(pl["lon"], pl["lat"])
        r = 9 + 5.5 * len(pl["lines"])
        obsazeno.append((x - r, y - 9, x + r, y + 9))
    # popisky bez překrývání: obce s víc předky dřív, zkusit vpravo, vlevo, nad, pod; co se nevejde, zůstane jen tečka
    poradi = sorted(range(len(places)), key=lambda i: -sum(len(g["people"]) for g in places[i]["lines"]))
    for i in poradi:
        pl = places[i]
        x, y = P(pl["lon"], pl["lat"])
        n = len(pl["lines"])
        w, h, dx = 9.2 * len(pl["name"]), 18, 8 + 5.5 * n
        for tx, ty, anchor, x0 in ((x + dx, y + 6, "start", x + dx), (x - dx, y + 6, "end", x - dx - w),
                                  (x, y - 14, "middle", x - w / 2), (x, y + 28, "middle", x - w / 2)):
            box = (x0, ty - 14, x0 + w, ty - 14 + h)
            if box[0] >= 0 and box[2] <= Wd and box[1] >= 0 and box[3] <= Hd and not any(
                    box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for b in obsazeno):
                obsazeno.append(box)
                popisky.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anchor}">{e(pl["name"])}</text>')
                break
    for i, pl in enumerate(places):
        x, y = P(pl["lon"], pl["lat"])
        barvy = [barva(g["k"]) for g in pl["lines"]]
        n = len(barvy)
        hyp = ' fill="none" stroke-width="3" stroke-dasharray="4 3"' if pl["hypothesis"] else ' stroke="#fff" stroke-width="2"'
        kruhy = "".join(f'<circle cx="{x + (j - (n - 1) / 2) * 11:.1f}" cy="{y}" r="8"'
                        + (f' stroke="{c}"' if pl["hypothesis"] else f' fill="{c}"') + hyp + "/>" for j, c in enumerate(barvy))
        tecky.append(f'<a href="#{A["m"](i)}" xlink:href="#{A["m"](i)}"><title>{e(pl["name"])}</title>{kruhy}'
                     f'<circle cx="{x}" cy="{y}" r="20" fill="transparent"/></a>')
    seznam = ""
    for i, pl in sorted(enumerate(places), key=lambda x: x[1]["name"]):
        tecky_rodu = "".join(f'<i class="dot" style="background:{barva(g["k"])}"></i>' for g in pl["lines"])
        roky = "%d–%d" % tuple(pl["years"]) if pl["years"] else ""
        seznam += f'<a class="pl" href="#{A["m"](i)}">{tecky_rodu}<b>{e(pl["name"])}</b><span>{e(roky)}</span></a>'

    return (f'<h2 id="mapa">Kde žili naši předci</h2><p class="hint">Bez internetu: přibližný obrys Česka a obce, kde předci žili, '
            f'barevně podle rodů (prázdný kroužek = hypotéza). Klepnutím na tečku nebo obec uvidíte, kdo tam žil.</p>'
            f'<div class="mapbox"><svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {Wd} {Hd}" class="mapa">'
            f'<polygon points="{obrys}" class="cz"/><g class="lbl">{"".join(popisky)}</g>{"".join(tecky)}</svg></div>'
            f'<details><summary>Seznam obcí ({len(places)})</summary><div class="plist">{seznam}</div></details>')


# ---------- hlavní stránka ----------
def stranka(js):
    story = texts.get("pribeh.md", "") if conf.get("maPribeh") else ""
    pribeh_nazev = frontmatter(story, "title") or (conf.get("pribeh") or {}).get("menu") or "Příběh rodu"
    pribeh_lead = frontmatter(story, "lead")
    uvod = conf.get("uvod") or {}
    foto = obrazek(uvod.get("foto")) if uvod.get("foto") else ""
    stats = site["stats"]
    karty = conf.get("zajimavosti_na_uvodu") or []
    zaj = md(texts.get("zajimavosti.md", ""))
    otazky = [i for i in site["issues"] if not i["text"].startswith("Vyřešeno")]
    dotazy = md(texts.get("dotazy.md", ""), 4)
    denik = "" if BEZ_DENIKU else md(texts.get("denik.md", ""))
    gens = sorted({p["gen"] for p in people.values() if p["gen"] > 0})

    # vějíř z fan_chart.py: odkazy na panely, kvůli starším prohlížečům i xlink:href
    hrefs = os.path.join(TMP, "hrefs.json")
    json.dump({str(k): "#" + A["o"](s) for k, s in slug_k.items()}, open(hrefs, "w"))
    fan = os.path.join(TMP, "fan.svg")
    subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(TOOLS, "fan_chart.py"), fan, "--web", hrefs],
                   check=True, stdout=subprocess.DEVNULL)
    svg = open(fan, encoding="utf-8").read()
    svg = svg.replace('<svg xmlns="http://www.w3.org/2000/svg"', '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"', 1)
    svg = re.sub(r'<a href="(#[^"]+)"', r'<a href="\1" xlink:href="\1"', svg)
    legenda = "".join(f'<span><i class="dot" style="background:{l["color"]}"></i>{e(l["name"])}</span>' for l in sorted(lines.values(), key=lambda l: l["k"]))

    obsah = [("pribeh", pribeh_nazev, story), ("vejir", "Vějíř předků", True), ("strom", "Stromový graf", js), ("predci", "Předci", True),
             ("rody", "Rody", lines), ("mapa", "Mapa", places), ("zajimavosti", "Zajímavosti", zaj), ("hledame", "Co hledáme", otazky or dotazy),
             ("zapisy", "Zápisy", recs), ("dokumenty", "Dokumenty", site["docs"]), ("denik", "Deník", denik)]
    nav = "".join(f'<a href="#{i}"' + (' class="jsonly"' if i == "strom" else "") + f'>{e(t)}</a> ' for i, t, ok in obsah if ok)

    rody = []
    for strana, filtr in (("Po otci", lambda k: k < 12), ("Po matce", lambda k: k >= 12)):
        sk = [l for l in sorted(lines.values(), key=lambda l: l["k"]) if filtr(l["k"])]
        if not sk:
            continue
        rody.append(f"<h3>{strana}</h3>")
        for l in sk:
            hyp = "".join(
                f'<h4>{e(h["title"])}</h4>' + (f'<p>{inline(h["text"])}</p>' if h["text"] else "")
                + ("<ul class=facts>" + "".join(f"<li><b>{e(i['name'])}</b> – {inline(i['text'])}</li>" for i in h["items"]) + "</ul>" if h["items"] else "")
                + ("<div class=recs>" + "".join(reclink(r) for r in h["records"] if r in recs) + "</div>" if h["records"] else "")
                for h in site["hypotheses"] if h["line"] == l["k"])
            rody.append(f'<div class="card line" id="{A["rod"](l["slug"])}" style="border-left-color:{l["color"]}"><h4>{e(l["name"])}</h4>'
                        f'<p class="small">{e(l["desc"])}</p><p class="small muted">{len(l["people"])} předků · začíná u {plink(l["root"])}</p>{hyp}</div>')

    predci = []
    for g in gens:
        lidi = sorted((p for p in people.values() if p["gen"] == g), key=lambda p: p["k"])
        polozky = "".join(f'<a class="pl" href="#{A["o"](p["slug"])}"><i class="dot" style="background:'
                          f'{line_by_k[p["line"]]["color"] if p["line"] in line_by_k else "#C9B9A3"}"></i><b>{e(p["name"])}</b><span>{e(p["years"])}</span></a>'
                          for p in lidi)
        predci.append(f'<details{" open" if g <= 3 else ""}><summary>{e(W_GEN(g))} <span class="cnt">({len(lidi)} z {2 ** g})</span></summary>'
                      f'<div class="plist">{polozky}</div></details>')

    druhy = sorted({r["kindName"] for r in recs.values()})
    zapisy = sorted(recs.values(), key=lambda r: datekey(r["date"]))
    zap_rows = "".join(
        f'<tr data-kind="{e(r["kindName"])}"><td class="nw">{e(r["date"])}</td><td>{e(r["kindName"])}</td>'
        f'<td><a href="#{A["z"](r["key"])}">{e(r["title"])}</a><div class="small muted">{e(r["volume"] or r["vdesc"])}</div></td>'
        f'<td class="small">{", ".join(plink(s, False) for s in r["people"] if s in people)}</td></tr>' for r in zapisy)

    dokumenty = "".join(
        f'<figure id="{A["d"](d["img"])}">' + (f'<div class="imgwrap"><img loading="lazy" src="{obrazek(d["img"])}" alt="{e(d["caption"])}"></div>' if obrazek(d["img"]) else "")
        + f'<figcaption>{e(d["caption"])}' + (" – " + ", ".join(plink(s, False) for s in d["people"]) if d["people"] else "") + "</figcaption></figure>"
        for d in site["docs"])

    hledani = (f'<div class="tools jsonly"><input id="q" type="search" placeholder="Hledat (jméno, místo, rok, zápis…)" autocomplete="off">'
               f'<button id="zin" aria-label="Přiblížit">+</button><button id="zout" aria-label="Oddálit">−</button><button id="zreset">Celý vějíř</button></div>'
               f'<div id="hits" class="jsonly"></div>') if js else ""
    nojs = ('<p class="nojs">Tahle verze je bez JavaScriptu: vějíř zvětšíte roztažením dvou prstů a na jména se dá klepat; '
            'pohodlnější je <a href="#predci">seznam předků</a>. Hledání a stromový graf má verze rodokmen.html.</p>')
    strom = (f'<section id="strom" class="jsonly"><h2>Stromový graf</h2><p class="hint">Rodiče nad dítětem. Tlačítkem nad osobou '
             f'rozbalíte/sbalíte její předky, pod jménem její sourozence. Dvěma prsty nebo kolečkem přibližujete, tažením posouváte.</p>'
             f'<div class="fan-btns"><button type="button" data-act="open">Rozbalit vše</button><button type="button" data-act="close">Sbalit vše</button>'
             f'<button type="button" data-act="fit">Celý</button><button type="button" data-act="root" hidden>Od začátku</button></div>'
             f'<div class="tree-stage"><div class="tree-canvas"><svg class="tree-lines"></svg></div><div class="tree-info" hidden></div></div></section>') if js else ""

    sheets = ([person_sheet(s, js) for s in sorted(people, key=lambda s: people[s]["k"])] + [family_sheet(f) for f in families]
              + [record_sheet(k) for k in recs] + [place_sheet(i, pl) for i, pl in enumerate(places)])
    kontakt = conf.get("kontakt") or {}
    pata = e(conf.get("zapati", "")) + (f' · Napište {e(kontakt.get("jmeno", ""))} na <a href="mailto:{e(kontakt["email"])}">{e(kontakt["email"])}</a>'
                                         if kontakt.get("email") else "")

    d = datetime.date.today()
    dnes = f"{d.day}. {d.month}. {d.year}"
    body = f"""<header id="uvod">
<h1>{e(conf.get("nazev", "Rodokmen"))}</h1>
<div class="teaser">
<div>{f'<h2 class="h2s">{e(uvod["nadpis"])}</h2>' if uvod.get("nadpis") else ""}{"".join(f"<p>{e(t)}</p>" for t in uvod.get("odstavce", []))}
{f'<p><a class="btn" href="#pribeh">{e((conf.get("pribeh") or {}).get("tlacitko") or "Přečíst: " + pribeh_nazev)} →</a></p>' if story else ""}</div>
{f'<figure><img src="{foto}" alt="{e(uvod.get("foto_popis", ""))}"><figcaption>{e(uvod.get("foto_popis", ""))}</figcaption></figure>' if foto else ""}
</div>
<div class="stats"><div><b>{stats["ancestors"]}</b>známých předků</div><div><b>{stats["documented"]}</b>doloženo matrikou</div>
<div><b>{stats["generations"]}</b>generací</div><div><b>{stats["records"]}</b>matričních zápisů</div></div>
{('<div class="cards">' + "".join(f'<a class="card" href="#zajimavosti"><h4>{e(c.get("nadpis"))}</h4><p class="small">{e(c.get("text"))}</p></a>' for c in karty) + "</div>") if karty else ""}
<nav class="toc">{nav}</nav>
</header>
<main>
{f'<h2 id="pribeh">{e(pribeh_nazev)}</h2>' + (f'<p class="lead">{e(pribeh_lead)}</p>' if pribeh_lead else "") + f'<div class="prose">{md(story)}</div>' if story else ""}
<h2 id="vejir">Vějíř předků</h2>
{'<noscript>' + nojs + '</noscript>' if js else nojs}
<p class="hint">Uprostřed {e(root["name"])}, každý prstenec je o generaci starší; vlevo otcova, vpravo matčina strana. Klepněte na jméno
pro podrobnosti{". Přibližujte tlačítkem +, dvěma prsty nebo kolečkem myši s klávesou Ctrl; tažením posunete" if js else ""}.</p>
{hledani}
<div class="fanbox" id="fanbox"><div class="fanin">{svg}</div></div>
<div class="legend">{legenda}</div>
{strom}
<h2 id="predci">Předci po generacích</h2>
{"".join(predci)}
{f'<h2 id="rody">Rody</h2><p class="hint">Rodokmen se větví podle pradědečků a prababiček – každý rod je jedna větev se všemi svými předky.</p>{"".join(rody)}' if lines else ""}
{mapa()}
{f'<h2 id="zajimavosti">Zajímavosti</h2><div class="prose">{zaj}</div>' if zaj else ""}
{f'<h2 id="hledame">Co ještě hledáme</h2>' + ('<div class="cards">' + "".join(f'<div class="card"><h4>{e(i["title"])}</h4><p class="small">{inline(i["text"])}</p></div>' for i in otazky) + "</div>" if otazky else "") + (f'<h3>Prameny mimo online matriky</h3><div class="prose small">{dotazy}</div>' if dotazy else "") if otazky or dotazy else ""}
<h2 id="zapisy">Zápisy z matrik ({len(recs)})</h2>
{('<p class="chips jsonly" id="kinds"><button class="chip" data-k="" type="button">vše</button>' + "".join(f'<button class="chip" data-k="{e(k)}" type="button">{e(k)}</button>' for k in druhy) + "</p>") if js else ""}
<div class="tbox"><table class="zap"><thead><tr><th>Datum</th><th>Druh</th><th>Zápis</th><th>Týká se</th></tr></thead><tbody>{zap_rows}</tbody></table></div>
{f'<h2 id="dokumenty">Rodinné dokumenty</h2><div class="docs">{dokumenty}</div>' if dokumenty else ""}
{f'<h2 id="denik">Výzkumný deník</h2><details><summary>Všechna hledání v matrikách včetně neúspěšných</summary><div class="small">{denik}</div></details>' if denik else ""}
</main>
<footer>{pata}<br><span class="small">Vytvořeno {dnes} z dat rodokmenu.</span></footer>
{"".join(sheets)}
<div id="zoom"></div>"""
    return body


def W_GEN(g):
    return {1: "Rodiče", 2: "Prarodiče", 3: "Praprarodiče"}.get(g, f"{g}. generace ({'pra' * (g - 1)}rodiče)")


def datekey(d):
    y = (re.search(r"\d{4}", d or "") or [None])[0] or "9999"
    parts = re.findall(r"\d+", (d or "").replace(y, "", 1))
    dd, mm = (parts[0], parts[1]) if len(parts) >= 2 else (0, parts[0] if parts else 0)
    return int(y) * 10000 + int(mm) * 100 + int(dd)


def css_stromu():
    t = open(os.path.join(WEBSRC, "styles", "global.css"), encoding="utf-8").read()
    m = re.search(r"/\* strom: začátek.*?\*/(.*?)/\* strom: konec \*/", t, re.S)
    return m.group(1) if m else ""


CSS = """
:root{--bg:#fbf8f2;--paper:#fff;--ink:#2b2620;--muted:#6e6153;--line:#e4ddd1;--accent:#8a5a2b;--accent-soft:#f3e6d4;--doc:#3f7d4a;
--prob:#b07a1e;--unk:#8a8278;--sans:"Helvetica Neue",Helvetica,Arial,sans-serif;--serif:Georgia,"Times New Roman",serif}
*{box-sizing:border-box}
[hidden]{display:none!important}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
html,body{margin:0;background:#fbf8f2;background:var(--bg);color:#2b2620;color:var(--ink);font:16px/1.55 "Helvetica Neue",Helvetica,Arial,sans-serif}
body{word-wrap:break-word;overflow-wrap:break-word}   /* dlouhá slova (praprapra…rodiče) nesmí rozšířit stránku */
header,main{max-width:1100px;margin:0 auto;padding:0 16px}
header{padding-top:28px}
h1{font:600 34px/1.1 Georgia,"Times New Roman",serif;font-size:clamp(28px,7vw,44px);margin:0 0 10px}
h2{font:600 26px/1.2 Georgia,serif;margin:44px 0 12px}
h3{font:600 19px/1.3 Georgia,serif;margin:22px 0 8px} h4{margin:0 0 4px;font-size:16px} .h2s{margin-top:8px;font-size:22px}
a{color:#8a5a2b;color:var(--accent)} summary{cursor:pointer}
.muted{color:#6e6153;color:var(--muted)} .small{font-size:14px} .nw{white-space:nowrap}
.teaser{display:-webkit-box;display:flex;flex-wrap:wrap;align-items:flex-start}
.teaser>div{flex:1 1 320px;margin-right:16px;max-width:760px} .teaser figure{flex:0 1 360px;margin:8px 0}
.teaser img{width:100%;height:auto;border-radius:10px;display:block} figcaption{font-size:14px;color:#6e6153;margin-top:4px}
.stats{display:flex;flex-wrap:wrap;margin:14px 0 6px}
.stats div{background:#f3e6d4;border-radius:10px;padding:8px 14px;margin:0 10px 10px 0} .stats b{font-size:20px;display:block}
.toc{margin:10px 0 0;line-height:2}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));grid-gap:10px;gap:10px;margin:8px 0 12px}
.card{display:block;background:#fff;border:1px solid #e4ddd1;border-radius:10px;padding:12px 14px;color:inherit;text-decoration:none}
.card.direct{border:2px solid #8a5a2b;background:#f3e6d4}
.card.line{border-left-width:6px;margin:0 0 10px}
.chips{margin:6px 0} .chips>*{margin:0 6px 6px 0}
.chip,.badge{display:inline-block;font-size:13px;padding:2px 9px;border-radius:20px;background:#f1e8da;color:inherit;text-decoration:none;border:0;font-family:inherit}
.st-doc{background:#ddebd3} .st-prob,.st-mh{background:#f4e3c2} .st-fam{background:#e6edf5} .st-unk{background:#e8e4de}
.dot{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:6px;vertical-align:-1px}
button,.btn{font:inherit;font-size:15px;border:1px solid #e4ddd1;background:#fff;border-radius:8px;padding:7px 12px;cursor:pointer;color:#2b2620;
  text-decoration:none;display:inline-block;-webkit-appearance:none;appearance:none;margin:0 6px 6px 0}
.btn.off{color:#6e6153;cursor:default}
html:not(.js) .jsonly{display:none!important}
.tools{display:flex;flex-wrap:wrap;align-items:center;margin:8px 0}
.tools input{flex:1 1 200px;min-width:0;padding:9px 12px;border:1px solid #e4ddd1;border-radius:8px;font:inherit;font-size:16px;background:#fff;
  -webkit-appearance:none;appearance:none;margin:0 6px 6px 0}
#hits a{padding:4px 10px;font-size:14px}
.fanbox{position:relative;width:100%;max-width:92vh;margin:0 auto;background:#fbf8f2;border:1px solid #e4ddd1;border-radius:14px;overflow:hidden}
.fanbox:before{content:"";display:block;padding-top:100%}
.fanin{position:absolute;top:0;left:0;right:0;bottom:0}
.js .fanbox{touch-action:pan-x pan-y;cursor:grab} .js .fanbox.zoomed{touch-action:none}
.fanbox svg{width:100%;height:100%;display:block;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}
.fan-links path,.fan-links circle{fill:transparent;cursor:pointer}
@media (hover:hover){.fan-links a:hover path,.fan-links a:hover circle{fill:rgba(138,75,42,.18)}}
.fan-links a.hit path,.fan-links a.hit circle{fill:rgba(220,60,30,.35)}
.legend{display:flex;flex-wrap:wrap;font-size:14px;color:#6e6153;margin:10px 0} .legend span{margin:0 16px 6px 0}
.hint{font-size:14px;color:#6e6153;max-width:760px}
.nojs{background:#f4e3c2;border-radius:8px;padding:10px 12px;font-size:15px}
main>details{border-top:1px solid #e4ddd1;padding:6px 0}
main>details>summary{font:600 18px/1.4 Georgia,serif;padding:6px 0} .cnt{color:#6e6153;font:14px sans-serif}
.plist{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));grid-gap:6px;gap:6px;margin:6px 0 10px}
.pl{display:flex;align-items:baseline;text-decoration:none;color:#2b2620;background:#fff;border:1px solid #e4ddd1;border-radius:8px;padding:8px 10px}
.pl b{flex:1;min-width:0;margin-right:6px} .pl span{color:#6e6153;font-size:14px;white-space:nowrap}
.lead{font:italic 18px/1.5 Georgia,serif;max-width:760px;color:#4a3f35}
.prose{max-width:760px} .prose h3{margin-top:24px} .prose p{margin:0 0 10px}
blockquote{margin:8px 0;padding:6px 12px;border-left:3px solid #e4ddd1;color:#4a3f35}
.tbox{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:8px 0}
table{border-collapse:collapse;width:100%;font-size:14px} th,td{border-bottom:1px solid #e4ddd1;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#f3e6d4}
.mapbox{background:#f4f4f2;border:1px solid #e4ddd1;border-radius:14px;overflow:hidden;max-width:760px}
.mapa{display:block;width:100%;height:auto} .mapa .cz{fill:#f3ede3;stroke:#b9ab98;stroke-width:2}
.mapa .lbl text{font:17px "Helvetica Neue",Arial,sans-serif;fill:#4a3f35;paint-order:stroke;stroke:#fff;stroke-width:4px}
.docs{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));grid-gap:12px;gap:12px} .docs figure{margin:0}
.sheet{display:none;position:fixed;top:0;right:0;bottom:0;width:560px;max-width:100%;height:100%;height:100dvh;background:#fffdf9;
  box-shadow:-8px 0 30px rgba(0,0,0,.15);overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;z-index:10;
  padding:0 20px 60px;padding-bottom:calc(60px + env(safe-area-inset-bottom))}
html:not(.js) .sheet:target,.sheet.show{display:block}
.sheet .bar{position:-webkit-sticky;position:sticky;top:0;background:#fffdf9;padding:12px 0 8px;padding-top:calc(12px + env(safe-area-inset-top));
  text-align:right;z-index:2}
.sheet h2.pn{margin:0} .py{color:#6e6153;margin-bottom:6px} .stripe{height:4px;width:60px;border-radius:3px;margin-bottom:10px}
.nav{margin:12px 0} .nav .btn{font-size:14px;padding:5px 10px}
.facts{padding-left:20px} .note{color:#4a3f35;font-size:15px;background:#f7f1e7;border-radius:8px;padding:10px 12px}
.reclink{display:block;border:1px solid #e4ddd1;border-radius:8px;padding:8px 10px;margin:6px 0;text-decoration:none;background:#fff}
.reclink span{display:block;font-size:13px;color:#6e6153}
.recbody{border-top:1px solid #e4ddd1;margin-top:14px;padding-top:12px}
.meta{font-size:13px;color:#6e6153;word-wrap:break-word;overflow-wrap:anywhere}
.imgwrap{position:relative;margin:8px 0} .js .imgwrap{cursor:zoom-in} .imgwrap img{width:100%;height:auto;display:block;border-radius:6px}
.imgwrap .bx{position:absolute;border:2.5px solid #d0342c;border-radius:3px;pointer-events:none}
details{margin:6px 0} .recbody summary{color:#8a5a2b}
pre{white-space:pre-wrap;word-wrap:break-word;overflow-wrap:anywhere;font:13px/1.5 Menlo,Consolas,monospace;background:#f4eee4;padding:10px;border-radius:6px}
#zoom{position:fixed;top:0;right:0;bottom:0;left:0;background:rgba(20,15,10,.92);z-index:20;display:none;overflow:auto;-webkit-overflow-scrolling:touch}
#zoom .zw{position:relative;width:220%;max-width:1800px;margin:auto} #zoom img{width:100%;display:block} #zoom.open{display:block}
#strom .fan-btns{margin:8px 0} #strom .tree-stage{height:75vh;border:1px solid #e4ddd1;border-radius:14px}
footer{color:#6e6153;font-size:14px;text-align:center;padding:20px 16px 40px}
@media (max-width:640px){.sheet{padding-left:16px;padding-right:16px;box-shadow:none} h2{font-size:23px}}
"""


def skript(N):
    """JavaScript verze rodokmen.html: panely s historií, vějíř, hledání, filtr zápisů, zvětšení obrázku, strom.
    Jen funkce, které umějí i starší mobilní prohlížeče (žádné ?. ??)."""
    strom = open(os.path.join(WEBSRC, "lib", "strom.js"), encoding="utf-8").read().replace("export function", "function")
    hledat = []
    for p in people.values():
        hledat.append(["#" + A["o"](p["slug"]), p["name"] + (" (" + p["years"] + ")" if p["years"] else ""), " ".join([p["name"], p["y"]] + p["facts"]), p["k"]])
    for i, pl in enumerate(places):
        hledat.append(["#" + A["m"](i), "📍 " + pl["name"], pl["name"], 0])
    for r in recs.values():
        hledat.append(["#" + A["z"](r["key"]), "📜 " + r["title"] + " (" + r["date"] + ")", " ".join([r["title"], r["date"], r["summary"]]), 0])
    data = json.dumps(dict(H=hledat, N=N), ensure_ascii=False).replace("</", "<\\/")
    return f"""<script>
var DATA = {data};
{strom}
(function () {{
var $ = function (s) {{ return document.querySelector(s); }};
var each = function (s, f) {{ Array.prototype.forEach.call(document.querySelectorAll(s), f); }};
var SHEET = /^#(o|z|r|m)-/;
// --- panely: historie prohlížeče = tlačítko Zpět panel zavře
var opened = 0;
function showSheet(id) {{
  each(".sheet.show", function (s) {{ s.classList.remove("show"); }});
  var el = id && document.getElementById(id);
  if (!el || !el.classList.contains("sheet")) return false;
  if (!el.getAttribute("data-ready")) {{   // u předka vložit zápisy rovnou do panelu
    Array.prototype.forEach.call(el.querySelectorAll(".reclink[data-r]"), function (a) {{
      var src = document.getElementById("z-" + a.getAttribute("data-r"));
      if (src && el.id.indexOf("o-") === 0) a.parentNode.replaceChild(src.querySelector(".recbody").cloneNode(true), a);
    }});
    el.setAttribute("data-ready", "1");
  }}
  el.classList.add("show"); el.scrollTop = 0;
  return true;
}}
function go(id) {{
  if (!showSheet(id)) return;
  try {{ history.pushState({{ sheet: id }}, "", "#" + id); opened++; }} catch (err) {{}}
}}
function closeSheet() {{
  each(".sheet.show", function (s) {{ s.classList.remove("show"); }});
  if (opened > 0) {{ try {{ history.go(-opened); }} catch (err) {{}} opened = 0; return; }}
  try {{ history.replaceState(null, "", location.pathname + location.search); }} catch (err) {{}}
}}
window.addEventListener("popstate", function () {{
  opened = Math.max(0, opened - 1);
  if (!showSheet(location.hash.slice(1))) opened = 0;
}});
// --- vějíř: přiblížení a posun (myš, prsty, tlačítka)
var box = $("#fanbox"), svg = $("#fanbox svg");
var vb = svg.getAttribute("viewBox").split(/[\\s,]+/).map(Number), V0 = vb.slice(), V = vb.slice();
function setV() {{ svg.setAttribute("viewBox", V.join(" ")); box.classList.toggle("zoomed", V[2] < V0[2] * 0.99); }}
function zoomAt(f, cx, cy) {{
  var w = Math.min(V0[2], Math.max(V0[2] / 25, V[2] * f)), k = w / V[2];
  V = [cx - (cx - V[0]) * k, cy - (cy - V[1]) * k, w, w]; setV();
}}
function toSvg(x, y) {{ var r = box.getBoundingClientRect(); return [V[0] + (x - r.left) / r.width * V[2], V[1] + (y - r.top) / r.height * V[3]]; }}
box.addEventListener("wheel", function (ev) {{
  if (!ev.ctrlKey && !ev.metaKey && !box.classList.contains("zoomed")) return;
  ev.preventDefault(); var p = toSvg(ev.clientX, ev.clientY); zoomAt(Math.exp(ev.deltaY * 0.0015), p[0], p[1]);
}}, {{ passive: false }});
["gesturestart", "gesturechange"].forEach(function (t) {{ box.addEventListener(t, function (ev) {{ ev.preventDefault(); }}); }});
var ptrs = {{}}, moved = 0, pinch0 = null;
var n = function () {{ return Object.keys(ptrs).length; }};
if (window.PointerEvent) {{
  box.addEventListener("pointerdown", function (ev) {{ ptrs[ev.pointerId] = [ev.clientX, ev.clientY]; if (n() === 1) moved = 0; pinch0 = null; }});
  box.addEventListener("pointermove", function (ev) {{
    var prev = ptrs[ev.pointerId]; if (!prev) return;
    ptrs[ev.pointerId] = [ev.clientX, ev.clientY];
    var r = box.getBoundingClientRect();
    if (n() === 1) {{
      var dx = ev.clientX - prev[0], dy = ev.clientY - prev[1]; moved += Math.abs(dx) + Math.abs(dy);
      if (moved > 8 && (box.classList.contains("zoomed") || ev.pointerType === "mouse")) {{ V[0] -= dx / r.width * V[2]; V[1] -= dy / r.height * V[3]; setV(); }}
    }} else if (n() === 2) {{
      var k = Object.keys(ptrs), a = ptrs[k[0]], b = ptrs[k[1]], d = Math.sqrt(Math.pow(a[0] - b[0], 2) + Math.pow(a[1] - b[1], 2)); moved = 99;
      if (pinch0) {{ var p = toSvg((a[0] + b[0]) / 2, (a[1] + b[1]) / 2); zoomAt(pinch0 / d, p[0], p[1]); }}
      pinch0 = d;
    }}
  }});
  ["pointerup", "pointercancel", "pointerleave"].forEach(function (t) {{ box.addEventListener(t, function (ev) {{ delete ptrs[ev.pointerId]; pinch0 = null; }}); }});
}}
$("#zin").onclick = function () {{ zoomAt(0.6, V[0] + V[2] / 2, V[1] + V[3] / 2); }};
$("#zout").onclick = function () {{ zoomAt(1 / 0.6, V[0] + V[2] / 2, V[1] + V[3] / 2); }};
$("#zreset").onclick = function () {{ V = V0.slice(); setV(); }};
// --- strom
var strom = null;
try {{ strom = stromovyGraf({{ N: DATA.N, stage: $("#strom .tree-stage"), buttons: $("#strom .fan-btns"), hash: false }}); }} catch (err) {{ $("#strom").style.display = "none"; }}
// --- odkazy na panely (vějíř, seznamy, texty, tlačítka v panelu), strom od osoby
document.addEventListener("click", function (ev) {{
  var a = ev.target.closest ? ev.target.closest("a") : null; if (!a) return;
  var href = a.getAttribute("href") || "";
  if (href === "#_") {{ ev.preventDefault(); closeSheet(); }}
  else if (a.getAttribute("data-strom")) {{
    ev.preventDefault(); closeSheet();
    if (strom) {{ $("#strom").scrollIntoView(); strom.zobrazOd(Number(a.getAttribute("data-strom"))); }}
  }}
  else if (SHEET.test(href)) {{
    ev.preventDefault();
    if (a.closest(".fan-links") && moved > 8) return;
    go(href.slice(1));
  }}
  else if (href.charAt(0) === "#" && a.closest(".sheet")) {{   // z panelu na místo ve stránce (rod, dokument)
    ev.preventDefault();
    each(".sheet.show", function (s) {{ s.classList.remove("show"); }}); opened = 0;
    var t = document.getElementById(href.slice(1)); if (t) t.scrollIntoView();
  }}
}});
document.addEventListener("click", function (ev) {{
  var w = ev.target.closest ? ev.target.closest(".imgwrap") : null; if (!w) return;
  $("#zoom").innerHTML = '<div class="zw">' + w.innerHTML + "</div>"; $("#zoom").classList.add("open");
}});
$("#zoom").onclick = function () {{ $("#zoom").classList.remove("open"); }};
document.addEventListener("keydown", function (ev) {{
  if (ev.key !== "Escape") return;
  if ($("#zoom").classList.contains("open")) $("#zoom").classList.remove("open"); else closeSheet();
}});
// --- hledání (osoby, místa, zápisy)
var norm = function (s) {{ return (s.normalize ? s.normalize("NFD") : s).replace(/[\\u0300-\\u036f]/g, "").toLowerCase(); }};
var H = DATA.H.map(function (h) {{ return h.concat([norm(h[1] + " " + h[2])]); }});
$("#q").addEventListener("input", function (ev) {{
  var q = norm(ev.target.value.replace(/^\\s+|\\s+$/g, "")), hits = $("#hits"); hits.innerHTML = "";
  each(".fan-links a.hit", function (a) {{ a.classList.remove("hit"); }});
  if (q.length < 2) return;
  H.filter(function (h) {{ return h[4].indexOf(q) >= 0; }}).slice(0, 40).forEach(function (h) {{
    if (h[3]) {{ var s = svg.querySelector('a[href="' + h[0] + '"]'); if (s) s.classList.add("hit"); }}
    var a = document.createElement("a"); a.className = "btn"; a.href = h[0]; a.textContent = h[1]; hits.appendChild(a);
  }});
}});
// --- filtr zápisů podle druhu
each("#kinds button", function (b) {{
  b.addEventListener("click", function () {{
    var k = b.getAttribute("data-k");
    each("tr[data-kind]", function (tr) {{ tr.style.display = !k || tr.getAttribute("data-kind") === k ? "" : "none"; }});
  }});
}});
showSheet(location.hash.slice(1));
}})();
</script>"""


def strom_data():
    """Uzly pro lib/strom.js (stejně jako stránka /strom/ webu), odkazy vedou na panely v souboru."""
    N = {}
    for k, s in slug_k.items():
        p = people.get(s)
        if not p:
            continue
        alias = p["k"] != k
        N[str(k)] = dict(s="#" + A["o"](s), n=p["name"], y=p["years"], c=line_by_k[p["line"]]["color"] if p["line"] in line_by_k else None,
                         a=1 if alias else 0, fu=1 if p["fatherUnknown"] else 0, b=p.get("sibStatus", "none"),
                         sd=[] if alias else [dict(n=x["name"], r=x["rel"] or "vztah neuveden", y=x["years"], kind=x["kind"], t=x["text"],
                                                   f=x["facts"], st=x["status"],
                                                   z=[["#" + A["z"](r), recs[r]["date"]] for r in x["records"] if r in recs]) for x in p["side"]])
    return N


def main():
    if not BEZ_OBR and not MAGICK:
        sys.exit("Chybí ImageMagick (příkaz magick) na zmenšení obrázků. Nainstalujte ho (macOS: brew install imagemagick, "
                 "Windows: winget install ImageMagick.ImageMagick), nebo spusťte s --bez-obrazku.")
    upozorneni()
    os.makedirs(OUT, exist_ok=True)
    N = strom_data()
    hotovo = []
    for js in VERZE:
        body = stranka(js)
        page = ('<!doctype html>\n<html lang="cs"' + ("" if js else ' class="nojs"') + '><head><meta charset="utf-8">'
                f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
                f'<meta name="format-detection" content="telephone=no"><meta name="robots" content="noindex,nofollow">'
                f'<title>{e(conf.get("nazev", "Rodokmen"))}</title><style>{CSS}{css_stromu() if js else ""}</style>'
                + ('<script>document.documentElement.className = "js";</script>' if js else "")
                + f"</head><body>\n{body}\n" + (skript(N) if js else "") + "</body></html>")
        path = os.path.join(OUT, "rodokmen.html" if js else "rodokmen-bez-js.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
        hotovo.append(f"{path} ({os.path.getsize(path) / 1e6:.1f} MB)")
    shutil.rmtree(TMP, ignore_errors=True)
    print("\n".join(hotovo))
    print(f"{len(people)} osob, {len(families)} rodin, {len(recs)} zápisů, {len(places)} míst, {len(site['docs'])} dokumentů"
          + (", bez obrázků" if BEZ_OBR else f", {sum(1 for v in _obr.values() if v)} obrázků"))


if __name__ == "__main__":
    main()
