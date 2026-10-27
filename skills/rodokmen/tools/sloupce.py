#!/usr/bin/env python3
"""Pruhy sloupců z dvoustran a přiblížení řádku – levné čtení matrik po sloupcích (šetří tokeny).

Snímek ARON bývá dvoustrana. Nástroj z každé strany vyřízne zvolený sloupec (např. datum + číslo domu + jméno),
pruhy z mnoha snímků poskládá vedle sebe do jednoho listu a každý pruh označí číslem snímku a stranou (L/P).
Kandidáta pak přiblížíte příkazem zoom v plném rozlišení – jen ten jeden řádek, ne celý snímek.

Použití (z kořene projektu):
  python3 -I tools/sloupce.py listy <složka> <výstup> --snimky 20-60 [--x 0.04,0.42] [--y 0,1] [--strany LP|L|P|C]
                              [--puleni] [--vyska PX] [--na-list N] [--kontrast]
      složka     stažený svazek nebo složka se snímky .jpg (čísla snímků jako u nahledy.py)
      výstup     začátek názvu listů: pracovni/x/jmena → pracovni/x/jmena_01.jpg, jmena_02.jpg…
      --snimky   rozsah čísel snímků („20-60“, „5,7,9-12“, každý druhý „1-139/2“), výchozí všechny
      --x        sloupec jako zlomky šířky STRANY (0 = levý okraj strany, 1 = pravý); výchozí 0.04,0.42
      --y        výškový rozsah strany (výchozí celá 0,1)
      --strany   které strany dvoustrany (výchozí LP = obě); u snímku s jednou stranou dejte --strany C (celý snímek)
      --puleni   každou stranu rozdělí na horní a dolní půlku vedle sebe (vyšší rozlišení textu, víc pruhů)
      --vyska    výška pruhu v px (výchozí 1000 ≈ třetina plného rozlišení; čitelné u tabulek 19. stol.)
      --na-list  kolik pruhů na list (výchozí tolik, aby list měl nejvýš ~2000 px na šířku)
      --kontrast šedá + roztažení kontrastu (vybledlé a tmavé snímky)
      Vypíše, které snímky jsou na kterém listu.

  python3 -I tools/sloupce.py zoom <složka> <snímek> <L|P|C> <y0,y1> <výstup.jpg> [--x 0,1] [--kontrast]
      řádek (výškový pruh y0–y1 strany L/P, nebo celého snímku C) v plném rozlišení, šířka nejvýš 1600 px.

Tip: nejdřív `nahledy.py --oblast hlava` (kde jsou roky a obce), pak `listy` na sloupec s číslem domu a jménem,
pak `zoom` jen u kandidátů. Mapu knihy (snímek → rok/obec) zapiš do deníku, ať se příště nehledá znovu.
"""
import concurrent.futures as cf, math, os, shutil, subprocess, sys, tempfile
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I složku skriptu do sys.path nepřidá
from nahledy import MAX, PISMA, magick, rozsah, snimky


def dvojice(text, nazev):
    try:
        a, b = (float(v) for v in text.split(","))
    except ValueError:
        sys.exit(f"{nazev}: dva zlomky 0–1 oddělené čárkou, např. 0.05,0.45 (ne pixely)")
    if not 0 <= a < b <= 1:
        sys.exit(f"{nazev}: musí platit 0 ≤ první < druhý ≤ 1 (zlomky, ne pixely)")
    return a, b


def vyrez(strana, x, y):
    """Geometrie výřezu jako fx výrazy: strana L/P/C, x a y = zlomky strany."""
    s0, sw = {"L": (0, 0.5), "P": (0.5, 0.5), "C": (0, 1)}[strana]
    x0, x1 = s0 + sw * x[0], s0 + sw * x[1]
    return (f"%[fx:floor(w*{x1 - x0})]x%[fx:floor(h*{y[1] - y[0]})]"
            f"+%[fx:floor(w*{x0})]+%[fx:floor(h*{y[0]})]")


def opt(args, name, default=None, flag=False):
    if name in args:
        i = args.index(name)
        if flag:
            del args[i]
            return True
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


def listy(args):
    vyber = opt(args, "--snimky")
    x = dvojice(opt(args, "--x", "0.04,0.42"), "--x")
    y = dvojice(opt(args, "--y", "0,1"), "--y")
    strany = opt(args, "--strany", "LP").upper()
    puleni = opt(args, "--puleni", flag=True)
    na_list = opt(args, "--na-list")
    vyska = int(opt(args, "--vyska", "1000"))
    kontrast = opt(args, "--kontrast", flag=True)
    if len(args) != 2 or not set(strany) <= set("LPC"):
        sys.exit(__doc__)
    slozka, vystup = args
    M = magick()
    vse = snimky(slozka)
    cisla = rozsah(vyber, vse)
    if not cisla:
        sys.exit(f"Žádný snímek v rozsahu {vyber} (ve složce jsou {min(vse)}–{max(vse)}).")
    casti = [(y[0], (y[0] + y[1]) / 2), ((y[0] + y[1]) / 2, y[1])] if puleni else [y]
    pismo = next((p for p in PISMA if os.path.exists(p)), None)
    ukoly = [(n, s, i, yy) for n in cisla for s in strany for i, yy in enumerate(casti)]
    tmp = tempfile.mkdtemp(prefix="sloupce-")

    def pruh(u):
        n, s, i, yy = u
        out = os.path.join(tmp, f"{n:05d}{s}{i}.miff")
        # JPEG rovnou dekódovat zmenšený (jpeg:size) – na pruh výšky `vyska` nepotřebujeme plné rozlišení
        napoveda = math.ceil((vyska - 40) / (yy[1] - yy[0]) * 1.1)
        cmd = [M, "-define", f"jpeg:size={napoveda}x{napoveda}", vse[n], "-auto-orient",
               "-crop", vyrez(s, x, yy), "+repage"]
        if kontrast:
            cmd += ["-colorspace", "Gray", "-contrast-stretch", "2%x25%"]
        cmd += ["-resize", f"x{vyska - 40}", "-background", "white", "-gravity", "North", "-splice", "0x40",
                "-bordercolor", "#888888", "-border", "1"]
        if pismo:
            stit = f"{n}{s if s != 'C' else ''}" + ("ab"[i] if puleni else "")
            cmd += ["-font", pismo, "-pointsize", "30", "-fill", "#c0201a", "-annotate", "+0+4", stit]
        subprocess.run(cmd + [out], check=True)
        return out

    try:
        with cf.ThreadPoolExecutor(4) as ex:
            pruhy = list(ex.map(pruh, ukoly))
        sirka = int(subprocess.run([M, "-ping", pruhy[0], "-format", "%w", "info:"], capture_output=True, text=True).stdout)
        k = int(na_list) if na_list else max(1, 2000 // sirka)   # čtečka list stejně zmenší na ~1600 px
        os.makedirs(os.path.dirname(os.path.abspath(vystup)), exist_ok=True)
        for j in range(0, len(pruhy), k):
            out = f"{vystup}_{j // k + 1:02d}.jpg"
            subprocess.run([M, "-background", "white", *pruhy[j:j + k], "+append", "-quality", "82", out], check=True)
            a, b = ukoly[j][0], ukoly[min(j + k, len(ukoly)) - 1][0]
            print(f"{out}: snímky {a}–{b}" if a != b else f"{out}: snímek {a}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not pismo:
        print("(bez čísel snímků v obrázku – nenašel jsem písmo; pruhy jdou zleva doprava: snímek, strana L, P)")


def zoom(args):
    x = dvojice(opt(args, "--x", "0,1"), "--x")
    kontrast = opt(args, "--kontrast", flag=True)
    if len(args) != 5:
        sys.exit(__doc__)
    slozka, n, strana, yy, vystup = args
    strana = strana.upper()
    if strana not in ("L", "P", "C"):
        sys.exit("strana: L, P nebo C")
    vse = snimky(slozka)
    if int(n) not in vse:
        sys.exit(f"Snímek {n} ve složce není ({min(vse)}–{max(vse)}).")
    cmd = [magick(), vse[int(n)], "-auto-orient", "-crop", vyrez(strana, x, dvojice(yy, "y0,y1")), "+repage"]
    if kontrast:
        cmd += ["-colorspace", "Gray", "-contrast-stretch", "2%x25%"]
    os.makedirs(os.path.dirname(os.path.abspath(vystup)), exist_ok=True)
    subprocess.run(cmd + ["-resize", f"{MAX}x{MAX}>", "-quality", "85", vystup], check=True)
    print(vystup)


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("listy", "zoom"):
        sys.exit(__doc__)
    (listy if args[0] == "listy" else zoom)(args[1:])


if __name__ == "__main__":
    main()
