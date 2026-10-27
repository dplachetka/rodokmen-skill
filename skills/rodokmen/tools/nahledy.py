#!/usr/bin/env python3
"""Kontaktní listy ze stažených snímků: mřížka zmenšených výřezů z mnoha snímků v jednom obrázku.

Na jeden pohled je vidět rok, obec a číslo strany (záhlaví), nebo data a jména (levý sloupec) – celý snímek se pak
otevře jen u kandidáta. Šetří čas i tokeny, hlavně u pomocníků (otevírat desítky celých snímků je drahé).

Použití (z kořene projektu):
  python3 -I tools/nahledy.py <složka> <výstup> [--snimky 20-60] [--oblast hlava|levy|pravy|cely|scitani|x0,y0,x1,y1]
                              [--sloupcu N] [--sirka PX]
    složka    stažený svazek (ARON: soubory …_<KÓD>_00NNN_…; u sčítání lidu …_00010_… = snímek 1),
              nebo libovolná složka se snímky .jpg (číslo = poslední číslo v názvu: f067.jpg = snímek 67;
              když ho nemají všechny soubory nebo se opakuje, pořadí podle názvu)
    výstup    začátek názvu listů: pracovni/pom_x/hlava → pracovni/pom_x/hlava_01.jpg, hlava_02.jpg…
    --snimky  rozsah čísel snímků („20-60“, „5,7,9-12“, každý druhý „1-139/2“), výchozí všechny
    --oblast  co vyříznout z každého snímku (zlomky šířky a výšky 0–1):
                hlava  horní pruh (0,0,1,0.12) – rok, obec, číslo strany (výchozí)
                levy   levý sloupec (0,0,0.35,1) – datum, číslo domu, jméno
                pravy  pravá polovina (0.5,0,1,1)   cely  celý snímek
                scitani  sčítání 1921: číslo domu, obec a majitel z pravé půlky popisného archu
    --sloupcu kolik dílků vedle sebe, --sirka šířka dílku v px (výchozí podle oblasti)
Vypíše, které snímky jsou na kterém listu. List má nejvýš asi 1600 px na delší straně (víc by se při čtení stejně zmenšilo).
"""
import concurrent.futures as cf, glob, math, os, re, shutil, subprocess, sys, tempfile
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

OBLASTI = {"hlava": ((0, 0, 1, 0.12), 1, 1500), "levy": ((0, 0, 0.35, 1), 3, 500),
           "pravy": ((0.5, 0, 1, 1), 2, 780), "cely": ((0, 0, 1, 1), 2, 780),
           "scitani": ((0.52, 0.09, 0.95, 0.25), 2, 750)}
MAX = 1600     # delší strana listu
PISMA = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arial.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"]


def magick():
    m = (shutil.which("magick") or next(iter(sorted(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))), None)
         or (os.name != "nt" and shutil.which("convert")))   # ImageMagick 6 bez magick; na Windows je convert.exe jiný program
    if not m:
        sys.exit("Chybí ImageMagick (příkaz magick). Nainstaluj ho (macOS: brew install imagemagick, "
                 "Windows: winget install ImageMagick.ImageMagick a restart Claude Code) a spusť nástroj znovu.")
    return m


def snimky(slozka):
    """{číslo snímku: soubor}. ARON: pole …_<KÓD>_00NNN_…; když jsou všechna čísla násobky 10 (sčítání), děleno 10.
    Jinak poslední číslo v názvu (f067.jpg, snimek_12.jpg), když ho mají všechny soubory a žádné se neopakuje;
    jinak pořadí podle názvu."""
    soubory = sorted(f for f in glob.glob(os.path.join(slozka, "*")) if f.lower().endswith((".jpg", ".jpeg")))
    if not soubory:
        sys.exit(f"Ve složce {slozka} nejsou žádné snímky .jpg.")
    cisla = [re.search(r"_[A-Z0-9]{8}_(\d{5})_", os.path.basename(f)) for f in soubory]
    if all(cisla):
        n = [int(c.group(1)) for c in cisla]
        if all(x % 10 == 0 for x in n) and len(set(n)) == len(n):
            n = [x // 10 for x in n]
        if len(set(n)) == len(n):
            return dict(zip(n, soubory))
    cisla = [re.findall(r"\d+", os.path.splitext(os.path.basename(f))[0]) for f in soubory]
    if all(cisla):
        n = [int(c[-1]) for c in cisla]
        if len(set(n)) == len(n):
            return dict(zip(n, soubory))
    print("(čísla snímků = pořadí podle názvu – názvy souborů nemají každý vlastní číslo)")
    return {i: f for i, f in enumerate(soubory, 1)}


def rozsah(text, vse):
    if not text:
        return sorted(vse)
    out = set()
    for cast in text.split(","):
        cast, _, krok = cast.partition("/")
        a, _, b = cast.partition("-")
        out.update(range(int(a), int(b or a) + 1, int(krok or 1)))
    return sorted(n for n in out if n in vse)


def main():
    args = sys.argv[1:]

    def opt(name, default=None):
        if name in args:
            i = args.index(name)
            v = args[i + 1]
            del args[i:i + 2]
            return v
        return default
    vyber, oblast = opt("--snimky"), opt("--oblast", "hlava")
    sloupcu, sirka = opt("--sloupcu"), opt("--sirka")
    if len(args) != 2:
        sys.exit(__doc__)
    slozka, vystup = args
    if oblast in OBLASTI:
        box, s0, w0 = OBLASTI[oblast]
    else:
        box, s0, w0 = tuple(float(v) for v in oblast.split(",")), 2, 700
        if len(box) != 4 or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
            sys.exit("--oblast: čtyři zlomky 0–1 x0,y0,x1,y1 (ne pixely)")
    sloupcu, sirka = int(sloupcu or s0), int(sirka or w0)
    sloupcu = max(1, min(sloupcu, MAX // sirka))
    M = magick()
    vse = snimky(slozka)
    cisla = rozsah(vyber, vse)
    if not cisla:
        sys.exit(f"Žádný snímek v rozsahu {vyber} (ve složce jsou {min(vse)}–{max(vse)}).")
    pismo = next((p for p in PISMA if os.path.exists(p)), None)
    x0, y0, x1, y1 = box
    tmp = tempfile.mkdtemp(prefix="nahledy-")
    # JPEG rovnou dekódovat zmenšený (jpeg:size) – u velkých snímků až 5× rychlejší než plné rozlišení
    napoveda = math.ceil(sirka / (x1 - x0) * 1.1)

    def dilek(n):
        out = os.path.join(tmp, f"{n:05d}.jpg")
        cmd = [M, "-define", f"jpeg:size={napoveda}x{napoveda}", vse[n], "-auto-orient",
               "-crop", f"%[fx:floor(w*{x1 - x0})]x%[fx:floor(h*{y1 - y0})]+%[fx:floor(w*{x0})]+%[fx:floor(h*{y0})]",
               "+repage", "-resize", f"{sirka}x", "-bordercolor", "white", "-border", "4"]
        if pismo:
            cmd += ["-font", pismo, "-pointsize", "26", "-fill", "#c0201a", "-undercolor", "#ffffffd0",
                    "-gravity", "NorthWest", "-annotate", "+8+6", f" {n} "]
        subprocess.run(cmd + ["-quality", "82", out], check=True)
        return out

    try:
        with cf.ThreadPoolExecutor(4) as ex:
            dilky = dict(zip(cisla, ex.map(dilek, cisla)))
        vyska = max(int(subprocess.run([M, "-ping", f, "-format", "%h", "info:"], capture_output=True, text=True).stdout)
                    for f in list(dilky.values())[:5])
        radku = max(1, MAX // vyska)
        na_list = sloupcu * radku
        os.makedirs(os.path.dirname(os.path.abspath(vystup)), exist_ok=True)
        for i in range(0, len(cisla), na_list):
            cast = cisla[i:i + na_list]
            radky = []
            for r in range(0, len(cast), sloupcu):
                rf = os.path.join(tmp, f"r{i}_{r}.miff")
                subprocess.run([M, "-background", "white", *[dilky[n] for n in cast[r:r + sloupcu]], "+append", rf], check=True)
                radky.append(rf)
            out = f"{vystup}_{i // na_list + 1:02d}.jpg"
            subprocess.run([M, "-background", "white", *radky, "-append", "-quality", "82", out], check=True)
            print(f"{out}: snímky {cast[0]}–{cast[-1]}" if len(cast) > 1 else f"{out}: snímek {cast[0]}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not pismo:
        print("(bez čísel snímků v obrázku – nenašel jsem písmo; pořadí je zleva doprava, shora dolů)")


if __name__ == "__main__":
    main()
