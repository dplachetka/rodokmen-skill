#!/usr/bin/env python3
"""Celý rodokmen jako JEDEN soubor HTML ke sdílení (e-mail, flash, WhatsApp) – bez serveru a bez instalace.
Vějíř předků (klikací, přiblížení, hledání), seznam předků po generacích + u každého předka údaje, výřezy zápisů s rámečkem, přepis a překlad,
sourozenci, příběh rodu, zajímavosti. Obrázky jsou vložené přímo do souboru (zmenšené). Panely fungují i bez JavaScriptu
(přes #kotvy) – iPhone v náhledu souboru (Mail, Soubory, WhatsApp) JavaScript nespouští.
Použití: jeden_soubor.py [výstup.html] [--sirka 1000] [--kvalita 50] [--bez-obrazku]"""
import base64, html, json, os, re, subprocess, sys, tempfile, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I složku skriptu do sys.path nepřidá
from nacti_osoby import nacti_osoby

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
args = [a for a in sys.argv[1:]]


def opt(name, default):
    if name in args:
        i = args.index(name)
        val = args[i + 1]
        del args[i:i + 2]
        return val
    return default


SIRKA, KVALITA = int(opt("--sirka", 1000)), int(opt("--kvalita", 50))   # delší strana obrázku; barevné skeny jsou těžké
BEZ_OBR = "--bez-obrazku" in args
args = [a for a in args if not a.startswith("--")]
OUT = os.path.abspath(args[0]) if args else os.path.join(ROOT, "vystupy", "rodokmen.html")

LINE_COLORS = {8: "#EFB45F", 9: "#F09A78", 10: "#E58AA6", 11: "#B99AE0",
               12: "#86B8E8", 13: "#6FCBB9", 14: "#9CD17A", 15: "#D3D46A"}
STATUS = {"doc": "doloženo matrikou", "prob": "pravděpodobné", "fam": "údaj od rodiny",
          "mh": "jen z cizího rodokmenu", "unk": "neznámé"}
KINDS = {"N": "křest / narození", "O": "sňatek", "Z": "úmrtí", "I": "rejstřík", "S": "sčítání lidu", "J": "jiný pramen"}


def jload(name, default):
    path = os.path.join(DATA, name)
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


ns = nacti_osoby(DATA)
P, LINES, SIDE = ns["P"], ns.get("LINES", {}), ns.get("SIDE", [])
WEB = jload("web.json", {})
ZAZ = {z["klic"]: z for z in jload("zaznamy.json", [])}
SVAZ = jload("svazky.json", {})
PREP = jload("prepisy.json", {})
ZVYR = jload("zvyrazneni.json", {})

# 1) klikací vějíř z fan_chart.py (odkazy #o<číslo> zachytí skript stránky)
tmp = tempfile.mkdtemp(prefix="jeden-")
hrefs = os.path.join(tmp, "hrefs.json")
json.dump({str(k): f"#o{k}" for k in P}, open(hrefs, "w"))
fan_svg = os.path.join(tmp, "fan.svg")
subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "fan_chart.py"), fan_svg, "--web", hrefs],
               check=True, stdout=subprocess.DEVNULL)
svg = open(fan_svg, encoding="utf-8").read()


# 2) obrázky zmenšené a vložené jako data: URI
def obrazek(klic):
    src = os.path.join(ROOT, "vyrezy", klic + ".jpg")
    if BEZ_OBR or not os.path.exists(src):
        return ""
    dst = os.path.join(tmp, klic + ".jpg")
    subprocess.run(["magick", src, "-resize", f"{SIRKA}x{SIRKA}>", "-strip", "-interlace", "JPEG", "-sampling-factor", "4:2:0",
                    "-quality", str(KVALITA), dst], check=True)
    return "data:image/jpeg;base64," + base64.b64encode(open(dst, "rb").read()).decode()


def line_of(k):
    while k > 15:
        k //= 2
    return k if k >= 8 else None


pouzite = {r for p in P.values() for r in p.get("r", [])} | {r for s in SIDE for r in s.get("r", [])}
foto = (WEB.get("uvod") or {}).get("foto")
if foto:
    pouzite.add(foto)
records = {}
for klic in sorted(pouzite):
    z = ZAZ.get(klic)
    if not z:
        continue
    sv = SVAZ.get(z.get("svazek", ""), {})
    pr = PREP.get(klic, {})
    records[klic] = dict(
        t=z.get("nazev", klic), d=z.get("datum", ""), kind=KINDS.get(z.get("druh", "J"), ""),
        s=z.get("shrnuti", ""), url=z.get("odkaz") or sv.get("url", ""), snimek=z.get("snimek"),
        sv=" · ".join(x for x in (sv.get("archiv"), sv.get("svazek")) if x),
        orig=pr.get("orig", ""), cs=pr.get("cs", ""),
        box=(ZVYR.get(klic) or {}).get("boxes", []), img=obrazek(klic))

people = {}
for k, p in P.items():
    lk = line_of(k)
    people[k] = dict(n=p["n"], y=p.get("y", ""), st=p.get("st", "unk"), stl=STATUS.get(p.get("st", "unk"), ""),
                     f=p.get("f", []), note=p.get("note", ""), r=[r for r in p.get("r", []) if r in records],
                     line=LINES[lk][0] if lk in LINES else "", col=LINE_COLORS.get(lk, "#C9B9A3"),
                     side=[dict(n=s["n"], t=s.get("t", ""), r=[r for r in s.get("r", []) if r in records])
                           for s in SIDE if s.get("k") == k])

# 3) zajímavosti a příběh z markdownu (odkazy /osoba/<slug>/ → #o<číslo>; adresy stejně jako export_web.py)
def slugify(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


SAME = {int(a): int(c) for a, c in (ns.get("SAME") or {}).items()}
slug2k, used = {}, set()
for k in sorted(P):
    p = P[k]
    if p["n"].startswith(("otec neuveden", "matka neuvedena")) or p["n"] in ("", "?") or k in SAME:
        continue
    yv = (p.get("y") or "").strip()
    ys = [] if yv.startswith(("?", "†")) else re.findall(r"\d{4}", yv)
    s = slugify(p["n"] + (" " + ys[0] if ys else ""))
    if s in used or not s:
        s = f"{s}-{k}"
    used.add(s)
    slug2k[f"/osoba/{s}/"] = k


def md_inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    def link(m):
        k = slug2k.get(m.group(2))
        return f'<a href="#o{k}">{m.group(1)}</a>' if k in P else m.group(1)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, t)


def md_bloky(path):
    if not os.path.exists(path):
        return ""
    txt = re.sub(r"<!--.*?-->", "", open(path, encoding="utf-8").read(), flags=re.S)
    txt = re.sub(r"\A---\n.*?\n---\n", "", txt, flags=re.S)   # hlavička příběhu (title, lead)
    out = []
    for blok in re.split(r"\n\s*\n", txt):
        blok = blok.strip()
        if not blok or blok.startswith("# "):
            continue
        if blok.startswith("## "):
            nadpis, _, zbytek = blok.partition("\n")
            out.append(f"<h3>{md_inline(nadpis[3:])}</h3>")
            blok = zbytek.strip()
            if not blok:
                continue
        out.append(f"<p>{md_inline(' '.join(blok.split()))}</p>")
    return "\n".join(out)


zajimavosti = md_bloky(os.path.join(DATA, "zajimavosti.md"))
pribeh_md = os.path.join(DATA, "pribeh.md")
pribeh = md_bloky(pribeh_md)
hlava = open(pribeh_md, encoding="utf-8").read() if pribeh else ""
pribeh_nazev = (re.search(r"^title:\s*(.+)$", hlava, re.M) or [None, (WEB.get("pribeh") or {}).get("menu") or "Příběh rodu"])[1].strip()
pribeh_lead = (re.search(r"^lead:\s*(.+)$", hlava, re.M) or [None, ""])[1].strip()
uvod = WEB.get("uvod") or {}
nazev = WEB.get("nazev", "Rodokmen")
legenda = "".join(f'<span><i style="background:{LINE_COLORS[k]}"></i>{html.escape(LINES[k][0])}</span>'
                  for k in sorted(LINES) if k in LINE_COLORS)
stat_doc = sum(1 for p in P.values() if p.get("st") == "doc")
generaci = max(k.bit_length() for k in P)
e = lambda s: html.escape(str(s or ""))

# 4) panely jako hotové HTML: bez JavaScriptu se otevírají přes #kotvu (:target) – iPhone v náhledu souboru JS nespouští
kdo_zapis = {}
for k, p in people.items():
    for r in p["r"] + [r for s in p["side"] for r in s["r"]]:
        if k not in kdo_zapis.setdefault(r, []):
            kdo_zapis[r].append(k)


def rec_body(klic):
    r = records[klic]
    boxes = "".join(f'<span class="bx" style="left:{b[0] * 100:.1f}%;top:{b[1] * 100:.1f}%;'
                    f'width:{(b[2] - b[0]) * 100:.1f}%;height:{(b[3] - b[1]) * 100:.1f}%"></span>' for b in r["box"])
    img = (f'<div class="imgwrap"><img loading="lazy" decoding="async" src="{r["img"]}" alt="{e(r["t"])}">{boxes}</div>'
           if r["img"] else "")
    zdroj = e(r["sv"]) + (f", snímek {e(r['snimek'])}" if r["snimek"] else "")
    if r["url"]:
        zdroj += f' · <a href="{e(r["url"])}" target="_blank" rel="noopener">otevřít v archivu</a>'
    shrnuti = f"<p>{e(r['s'])}</p>" if r["s"] else ""
    preklad = f"<details><summary>Překlad do češtiny</summary><pre>{e(r['cs'])}</pre></details>" if r["cs"] else ""
    prepis = f"<details><summary>Přepis originálu</summary><pre>{e(r['orig'])}</pre></details>" if r["orig"] else ""
    meta = e(" · ".join(x for x in (r["kind"], r["d"]) if x))
    return (f'<div class="recbody"><h4>{e(r["t"])}</h4><div class="meta">{meta}</div>'
            f'{img}{shrnuti}{preklad}{prepis}<div class="meta">{zdroj}</div></div>')


def rec_link(klic):
    r = records[klic]
    return (f'<a class="reclink" href="#z_{klic}" data-r="{klic}">{e(r["t"])}'
            f'<span>{e(" · ".join(x for x in (r["kind"], r["d"]) if x))}</span></a>')


CLOSE = '<div class="bar"><a class="btn close" href="#_" aria-label="Zavřít">✕ Zavřít</a></div>'
sheets = []
for klic in records:
    lidi = "".join(f'<a class="btn" href="#o{k}">{e(people[k]["n"])}</a>' for k in kdo_zapis.get(klic, []))
    lidi = f"<h3>Kdo je v zápisu</h3><div class=nav>{lidi}</div>" if lidi else ""
    sheets.append(f'<section class="sheet" id="z_{klic}">{CLOSE}{rec_body(klic)}{lidi}</section>')
for k, p in sorted(people.items()):
    nav = "".join(f'<a class="btn" href="#o{c}">{lab}: {e(people[c]["n"])}</a>'
                  for c, lab in ((2 * k, "Otec"), (2 * k + 1, "Matka"), (k // 2, "Dítě")) if c >= 1 and c != k and c in people)
    side = "".join(f'<div class="sib"><b>{e(s["n"])}</b> – {e(s["t"])}</div>'   # zápis, který je i u předka, jen jednou
                   f'<div class="recs">{"".join(rec_link(r) for r in s["r"] if r not in p["r"])}</div>' for s in p["side"])
    rod = f'<span class="badge">rod {e(p["line"])}</span>' if p["line"] else ""
    fakta = "<ul class=facts>" + "".join(f"<li>{e(x)}</li>" for x in p["f"]) + "</ul>" if p["f"] else ""
    pozn = f'<div class="note">{e(p["note"])}</div>' if p["note"] else ""
    side = f"<h3>Sourozenci a příbuzní</h3>{side}" if side else ""
    zap = "<h3>Zápisy z archivů</h3><div class=recs>" + "".join(rec_link(r) for r in p["r"]) + "</div>" if p["r"] else ""
    sheets.append(
        f'<section class="sheet" id="o{k}">{CLOSE}<div class="stripe" style="background:{p["col"]}"></div>'
        f'<h2 class="pn">{e(p["n"])}</h2><div class="py">{e(p["y"])}</div>'
        f'<span class="badge st-{p["st"]}">{e(p["stl"])}</span>{rod}<div class="nav">{nav}</div>'
        f'{fakta}{pozn}{side}{zap}</section>')

# 5) seznam předků po generacích – na telefonu čitelnější než vějíř
GEN = {1: "Rodiče", 2: "Prarodiče", 3: "Praprarodiče"}
seznam = []
for g in range(1, generaci):
    lidi = [k for k in sorted(people) if k.bit_length() - 1 == g]
    if not lidi:
        continue
    polozky = "".join(f'<a class="pl" href="#o{k}"><i style="background:{people[k]["col"]}"></i>'
                      f'<b>{e(people[k]["n"])}</b><span>{e(people[k]["y"])}</span></a>' for k in lidi)
    seznam.append(f'<details{" open" if g <= 3 else ""}><summary>{GEN.get(g, f"{g}. generace")} '
                  f'<span class="cnt">({len(lidi)})</span></summary><div class="plist">{polozky}</div></details>')

search = {k: dict(n=p["n"], y=p["y"], f=" ".join(p["f"])) for k, p in people.items()}
data_js = json.dumps(search, ensure_ascii=False).replace("</", "<\\/")

page = f"""<!doctype html>
<html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(nazev)}</title>
<style>
:root{{--bg:#FBF8F2;--panel:#FFFDF9;--ink:#2A231C;--muted:#7A6B5B;--line:#E4DACB;--acc:#8A4B2A;--chip:#F1E8DA}}
*{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%;text-size-adjust:100%}}
html,body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 "Helvetica Neue",Helvetica,Arial,sans-serif}}
header{{max-width:1100px;margin:0 auto;padding:28px 16px 8px}}
h1{{font:600 clamp(28px,7vw,44px)/1.1 Georgia,"Times New Roman",serif;margin:0 0 6px}}
h2{{font:600 26px/1.2 Georgia,serif;margin:40px 0 12px}}
.uvod{{max-width:760px}} .uvod h2{{margin-top:18px;font-size:22px}}
.stats{{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}}
.stats div{{background:var(--chip);border-radius:10px;padding:8px 14px}} .stats b{{font-size:20px;display:block}}
main{{max-width:1100px;margin:0 auto;padding:0 16px 60px}}
.tools{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}}
.tools input{{flex:1;min-width:180px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;font:inherit;font-size:16px;background:#fff;-webkit-appearance:none}}
button,.btn{{font:inherit;font-size:15px;border:1px solid var(--line);background:#fff;border-radius:8px;padding:7px 12px;cursor:pointer;color:var(--ink);
  text-decoration:none;display:inline-block;-webkit-appearance:none}}
html:not(.js) .tools,html:not(.js) #hits{{display:none}}
#hits{{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0}} #hits a{{padding:4px 10px;font-size:14px}}
.fanbox{{position:relative;width:100%;aspect-ratio:1/1;max-height:92vh;margin:0 auto;background:var(--bg);border:1px solid var(--line);
  border-radius:14px;overflow:hidden}}
.js .fanbox{{touch-action:pan-x pan-y;cursor:grab}} .js .fanbox.zoomed{{touch-action:none}}
.fanbox svg{{width:100%;height:100%;display:block;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}}
.fan-links path,.fan-links circle{{fill:transparent;cursor:pointer}}
@media (hover:hover){{.fan-links a:hover path,.fan-links a:hover circle{{fill:rgba(138,75,42,.18)}}}}
.fan-links a.hit path,.fan-links a.hit circle{{fill:rgba(220,60,30,.35)}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:14px;color:var(--muted);margin:10px 0}}
.legend i,.pl i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px;flex:none}}
.hint{{font-size:14px;color:var(--muted)}}
.nojs{{background:#F4E3C2;border-radius:8px;padding:10px 12px;font-size:15px}}
details.g,main>details{{border-top:1px solid var(--line);padding:6px 0}}
main>details>summary{{font:600 18px/1.4 Georgia,serif;padding:6px 0}} .cnt{{color:var(--muted);font:14px sans-serif}}
.plist{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:6px;margin:6px 0 10px}}
.pl{{display:flex;align-items:baseline;gap:4px;text-decoration:none;color:var(--ink);background:#fff;border:1px solid var(--line);
  border-radius:8px;padding:8px 10px}} .pl b{{flex:1;min-width:0}} .pl span{{color:var(--muted);font-size:14px;white-space:nowrap}}
.lead{{font:italic 18px/1.5 Georgia,serif;max-width:760px;color:#4A3F35}}
.zaj h3{{font:600 19px/1.3 Georgia,serif;margin:22px 0 4px}} .zaj p{{margin:0 0 8px;max-width:760px}}
a{{color:var(--acc)}} summary{{cursor:pointer}}
.sheet{{display:none;position:fixed;top:0;right:0;bottom:0;width:min(560px,100%);height:100%;height:100dvh;background:var(--panel);
  box-shadow:-8px 0 30px rgba(0,0,0,.15);overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;z-index:10;
  padding:0 20px calc(60px + env(safe-area-inset-bottom))}}
html:not(.js) .sheet:target,.sheet.show{{display:block}}
.sheet .bar{{position:sticky;top:0;background:var(--panel);padding:calc(12px + env(safe-area-inset-top)) 0 8px;text-align:right;z-index:2}}
.sheet h2.pn{{margin:0}} .py{{color:var(--muted);margin-bottom:6px}} .stripe{{height:4px;width:60px;border-radius:3px;margin-bottom:10px}}
.badge{{display:inline-block;font-size:13px;padding:2px 9px;border-radius:20px;background:var(--chip);margin:0 6px 4px 0}}
.st-doc{{background:#DDEBD3}} .st-prob,.st-mh{{background:#F4E3C2}} .st-unk{{background:#E8E4DE}}
.nav{{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}} .nav .btn{{font-size:14px;padding:5px 10px}}
.facts{{padding-left:20px}} .note{{color:#4A3F35;font-size:15px;background:#F7F1E7;border-radius:8px;padding:10px 12px}}
.reclink{{display:block;border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin:6px 0;text-decoration:none;background:#fff}}
.reclink span{{display:block;font-size:13px;color:var(--muted)}}
.recbody{{border-top:1px solid var(--line);margin-top:14px;padding-top:12px}}
.recbody h4{{margin:0 0 2px;font-size:16px}} .meta{{font-size:13px;color:var(--muted);overflow-wrap:anywhere}}
.imgwrap{{position:relative;margin:8px 0}} .js .imgwrap{{cursor:zoom-in}} .imgwrap img{{width:100%;height:auto;display:block;border-radius:6px}}
.imgwrap .bx{{position:absolute;border:2.5px solid #D0342C;border-radius:3px;pointer-events:none}}
details{{margin:6px 0}} .recbody summary{{color:var(--acc)}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.5 Menlo,Consolas,monospace;background:#F4EEE4;padding:10px;border-radius:6px}}
.sib{{font-size:15px;margin:8px 0 2px}}
#zoom{{position:fixed;inset:0;background:rgba(20,15,10,.92);z-index:20;display:none;overflow:auto;-webkit-overflow-scrolling:touch}}
#zoom .zw{{position:relative;width:min(1800px,220%);margin:auto}} #zoom img{{width:100%;display:block}} #zoom.open{{display:block}}
footer{{color:var(--muted);font-size:14px;text-align:center;padding:20px 16px 40px}}
@media (max-width:640px){{.sheet{{padding-left:16px;padding-right:16px;box-shadow:none}} h2{{font-size:23px}}}}
</style>
<script>document.documentElement.className = "js";</script>
</head><body>
<header>
<h1>{e(nazev)}</h1>
<div class="uvod">
{f'<h2>{e(uvod["nadpis"])}</h2>' if uvod.get("nadpis") else ""}
{"".join(f"<p>{e(t)}</p>" for t in uvod.get("odstavce", []))}
</div>
<div class="stats"><div><b>{len(P)}</b>předků</div><div><b>{stat_doc}</b>doloženo matrikou</div>
<div><b>{len(records)}</b>zápisů z archivů</div><div><b>{generaci}</b>generací</div></div>
<p>{f'<a href="#pribeh">{e(pribeh_nazev)}</a> · ' if pribeh else ""}<a href="#predci">Seznam předků</a>{' · <a href="#zajimavosti">Zajímavosti</a>' if zajimavosti else ""}</p>
</header>
<main>
<h2>Vějíř předků</h2>
<noscript><p class="nojs">Tento náhled neumí hledat ani přibližovat tlačítky – vějíř zvětšíte roztažením dvou prstů
a na jména se dá klepat. Pohodlnější je <a href="#predci">seznam předků</a> pod vějířem.</p></noscript>
<p class="hint">Uprostřed {e(P[1]["n"])}, každý prstenec je o generaci starší; vlevo otcova, vpravo matčina strana.
Klepněte na jméno pro podrobnosti. Přibližujte tlačítkem +, dvěma prsty nebo kolečkem myši s klávesou Ctrl; tažením posunete.
Kurzívou jsou údaje zatím jen pravděpodobné.</p>
<div class="tools"><input id="q" type="search" placeholder="Hledat předka (jméno, místo, rok…)" autocomplete="off">
<button id="zin" aria-label="Přiblížit">+</button><button id="zout" aria-label="Oddálit">−</button><button id="zreset">Celý vějíř</button></div>
<div id="hits"></div>
<div class="fanbox" id="fanbox">{svg}</div>
<div class="legend">{legenda}</div>
{f'<h2 id="pribeh">{e(pribeh_nazev)}</h2>' + (f'<p class="lead">{e(pribeh_lead)}</p>' if pribeh_lead else "") + f'<div class="zaj">{pribeh}</div>' if pribeh else ""}
<h2 id="predci">Seznam předků</h2>
{"".join(seznam)}
{f'<h2 id="zajimavosti">Zajímavosti</h2><div class="zaj">{zajimavosti}</div>' if zajimavosti else ""}
</main>
<footer>{e(WEB.get("zapati", ""))}</footer>
{"".join(sheets)}
<div id="zoom"></div>
<script>
const D = {data_js};
const $ = s => document.querySelector(s);
const svg = $("#fanbox svg"), box = $("#fanbox");

// --- panely: #o<číslo> = předek, #z_<klíč> = zápis; historie prohlížeče = tlačítko Zpět panel zavře
let opened = 0;
function showSheet(id) {{
  document.querySelectorAll(".sheet.show").forEach(s => s.classList.remove("show"));
  const el = id && document.getElementById(id);
  if (!el || !el.classList.contains("sheet")) return false;
  if (!el.dataset.ready) {{   // u předka vložit zápisy rovnou do panelu
    el.querySelectorAll(".reclink").forEach(a => {{
      const src = document.getElementById("z_" + a.dataset.r);
      if (src) a.replaceWith(src.querySelector(".recbody").cloneNode(true));
    }});
    el.dataset.ready = 1;
  }}
  el.classList.add("show"); el.scrollTop = 0;
  return true;
}}
function go(id) {{
  if (!showSheet(id)) return;
  try {{ history.pushState({{sheet: id}}, "", "#" + id); opened++; }} catch (err) {{}}
}}
function closeSheet() {{
  document.querySelectorAll(".sheet.show").forEach(s => s.classList.remove("show"));
  if (opened > 0) {{ try {{ history.go(-opened); }} catch (err) {{}} opened = 0; return; }}
  try {{ history.replaceState(null, "", location.pathname + location.search); }} catch (err) {{}}
}}
window.addEventListener("popstate", () => {{
  const id = location.hash.slice(1); opened = Math.max(0, opened - 1);
  if (!showSheet(id)) opened = 0;
}});

// --- přiblížení a posun vějíře (myš, prsty)
const full = svg.viewBox.baseVal; const V0 = [full.x, full.y, full.width, full.height]; let V = V0.slice();
function setV() {{ svg.setAttribute("viewBox", V.join(" ")); box.classList.toggle("zoomed", V[2] < V0[2] * 0.99); }}
function zoomAt(f, cx, cy) {{
  const w = Math.min(V0[2], Math.max(V0[2] / 25, V[2] * f));
  const k = w / V[2]; V = [cx - (cx - V[0]) * k, cy - (cy - V[1]) * k, w, w]; setV();
}}
function toSvg(x, y) {{ const r = box.getBoundingClientRect(); return [V[0] + (x - r.left) / r.width * V[2], V[1] + (y - r.top) / r.height * V[3]]; }}
box.addEventListener("wheel", ev => {{
  if (!ev.ctrlKey && !ev.metaKey && !box.classList.contains("zoomed")) return;
  ev.preventDefault(); const [x, y] = toSvg(ev.clientX, ev.clientY); zoomAt(Math.exp(ev.deltaY * 0.0015), x, y);
}}, {{passive: false}});
["gesturestart", "gesturechange"].forEach(t => box.addEventListener(t, ev => ev.preventDefault()));   // Safari: nezoomovat celou stránku
const ptrs = new Map(); let moved = 0, pinch0 = null;
box.addEventListener("pointerdown", ev => {{ ptrs.set(ev.pointerId, [ev.clientX, ev.clientY]); if (ptrs.size === 1) moved = 0; pinch0 = null; }});
box.addEventListener("pointermove", ev => {{
  if (!ptrs.has(ev.pointerId)) return;
  const prev = ptrs.get(ev.pointerId); ptrs.set(ev.pointerId, [ev.clientX, ev.clientY]);
  const r = box.getBoundingClientRect();
  if (ptrs.size === 1) {{
    const dx = ev.clientX - prev[0], dy = ev.clientY - prev[1]; moved += Math.abs(dx) + Math.abs(dy);
    if (moved > 8 && box.classList.contains("zoomed") || ev.pointerType === "mouse" && moved > 8) {{
      V[0] -= dx / r.width * V[2]; V[1] -= dy / r.height * V[3]; setV();
    }}
  }} else if (ptrs.size === 2) {{
    const [a, b] = [...ptrs.values()]; const d = Math.hypot(a[0] - b[0], a[1] - b[1]); moved = 99;
    if (pinch0) {{ const [x, y] = toSvg((a[0] + b[0]) / 2, (a[1] + b[1]) / 2); zoomAt(pinch0 / d, x, y); }}
    pinch0 = d;
  }}
}});
["pointerup", "pointercancel", "pointerleave"].forEach(t => box.addEventListener(t, ev => {{ ptrs.delete(ev.pointerId); pinch0 = null; }}));
$("#zin").onclick = () => zoomAt(0.6, V[0] + V[2] / 2, V[1] + V[3] / 2);
$("#zout").onclick = () => zoomAt(1 / 0.6, V[0] + V[2] / 2, V[1] + V[3] / 2);
$("#zreset").onclick = () => {{ V = V0.slice(); setV(); }};

// --- všechny odkazy na panely (vějíř, seznam, zajímavosti, tlačítka v panelu)
document.addEventListener("click", ev => {{
  const a = ev.target.closest("a"); if (!a) return;
  const href = a.getAttribute("href") || "";
  if (href === "#_") {{ ev.preventDefault(); closeSheet(); }}
  else if (/^#(o\\d+|z_)/.test(href)) {{
    ev.preventDefault();
    if (a.closest(".fan-links") && moved > 8) return;
    go(href.slice(1));
  }}
}});
document.addEventListener("click", ev => {{
  const w = ev.target.closest(".sheet .imgwrap"); if (!w) return;
  $("#zoom").innerHTML = '<div class="zw">' + w.innerHTML + '</div>'; $("#zoom").classList.add("open");
}});
$("#zoom").onclick = () => $("#zoom").classList.remove("open");
document.addEventListener("keydown", ev => {{
  if (ev.key !== "Escape") return;
  if ($("#zoom").classList.contains("open")) $("#zoom").classList.remove("open"); else closeSheet();
}});

// --- hledání
const norm = s => s.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase();
$("#q").addEventListener("input", ev => {{
  const q = norm(ev.target.value.trim()); const hits = $("#hits"); hits.innerHTML = "";
  svg.querySelectorAll(".fan-links a.hit").forEach(a => a.classList.remove("hit"));
  if (q.length < 2) return;
  Object.entries(D).filter(([k, p]) => norm([p.n, p.y, p.f].join(" ")).includes(q)).slice(0, 30).forEach(([k, p]) => {{
    svg.querySelector(`a[href="#o${{k}}"]`)?.classList.add("hit");
    const a = document.createElement("a"); a.className = "btn"; a.href = "#o" + k; a.textContent = `${{p.n}} (${{p.y}})`; hits.appendChild(a);
  }});
}});
showSheet(location.hash.slice(1));
</script>
</body></html>"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(page)
print(OUT, f"{os.path.getsize(OUT) / 1e6:.1f} MB,", len(people), "osob,", len(records), "zápisů")
