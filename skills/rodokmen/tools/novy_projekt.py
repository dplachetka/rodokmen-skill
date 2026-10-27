#!/usr/bin/env python3
"""Založí nový projekt rodokmenu ze šablony skillu.

Použití: python3 <skill>/tools/novy_projekt.py <cílová složka> [--ukazka]
  --ukazka   nakopíruje i vymyšlená ukázková data (rodina Novákových), aby šel web hned vyzkoušet

Vytvoří: data/ (prázdné kostry nebo ukázka), web/ (Astro web), tools/ (kopie nástrojů),
vyrezy/, zdroje/, dokumenty/, pracovni/, CLAUDE.md, .gitignore, .gitattributes (konce řádků LF i na Windows),
.claude/launch.json (náhled v Claude desktop), .claude/agents/ (pomocník ctenar-matrik) a .claude/cteni_matrik.md
(jeho návod ke čtení – kopie reference/matriky.md, při každé aktualizaci nová).
Existující data nepřepisuje.
Aktualizace staršího projektu (znovu spustit na stejnou složku): tools/ se přepíše vždy a soubory webu,
které se liší od nové šablony, taky – jejich staré verze se nejdřív uloží do pracovni/zaloha_web_<datum>/.
Nástroje upravené v projektu se před přepsáním uloží do pracovni/zaloha_nastroje_<datum>/ (pozná je podle otisků
v .skill_nastroje.json); nástroje, které skill nemá (vlastní skripty projektu), zůstanou beze změny.
"""
import filecmp, hashlib, json, os, shutil, sys, time
if sys.version_info < (3, 15):
    sys.exit(f"Rodokmen potřebuje Python 3.15 nebo novější, tohle je {sys.version.split()[0]}. "
             "Nainstalujte novější (macOS: brew install python, Windows: py install 3.15) a spusťte nástroj znovu.")
for _s in (sys.stdout, sys.stderr):   # UTF-8 výstup i na Windows bez -X utf8 (cp1250 neumí třeba „→“)
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def copy(src, out):
    if os.path.islink(out):   # nepsat přes symlink mimo projekt
        os.remove(out)
    shutil.copy2(src, out)


def fingerprint(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def copy_tree(src, dst, backup=None):
    """Zkopíruje chybějící soubory. S backup= přepíše i ty, které se liší, a starou verzi uloží do backup/."""
    changed = []
    for base, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "dist", ".astro", "__pycache__")]
        rel = os.path.relpath(base, src)
        os.makedirs(os.path.join(dst, rel), exist_ok=True)
        for f in files:
            new, out = os.path.join(base, f), os.path.join(dst, rel, f)
            if not os.path.lexists(out):
                copy(new, out)
            elif backup and (os.path.islink(out) or not filecmp.cmp(new, out, shallow=False)):
                keep = os.path.join(backup, os.path.normpath(os.path.join(rel, f)))
                os.makedirs(os.path.dirname(keep), exist_ok=True)
                if not os.path.islink(out):
                    shutil.copy2(out, keep)
                copy(new, out)
                changed.append(os.path.normpath(os.path.join(rel, f)))
    return changed


def doplnit_gitignore(dst):
    """Do .gitignore staršího projektu doplní vzory, které má nová šablona a projekt ne (vlastní řádky nechá)."""
    path = os.path.join(dst, ".gitignore")
    if not os.path.exists(path):
        return []
    mine = {l.strip() for l in open(path, encoding="utf-8").read().splitlines()}
    new = [l.strip() for l in open(os.path.join(SKILL, "template", ".gitignore"), encoding="utf-8").read().splitlines()
           if l.strip() and not l.startswith("#") and l.strip() not in mine]
    if new:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n# doplněno při aktualizaci skillu\n" + "\n".join(new) + "\n")
    return new


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    dst = os.path.abspath(os.path.expanduser(sys.argv[1]))
    demo = "--ukazka" in sys.argv
    os.makedirs(dst, exist_ok=True)
    # starší projekt: data/osoby.py → data/osoby.json dřív, než šablona přidá prázdný osoby.json
    sys.path.insert(0, os.path.join(SKILL, "tools"))
    from nacti_osoby import prevod
    try:
        if prevod(dst):
            print("data/osoby.py převedeno na data/osoby.json (původní soubor: pracovni/osoby_puvodni.py)")
    except ValueError as e:
        sys.exit(f"CHYBA při převodu data/osoby.py na osoby.json: {e}\nOpravte to a spusťte novy_projekt.py znovu.")
    copy_tree(os.path.join(SKILL, "template", "ukazka" if demo else "data"), os.path.join(dst, "data"))
    if demo:
        for sub in ("vyrezy", "zdroje"):
            src = os.path.join(SKILL, "template", "ukazka_" + sub)
            if os.path.isdir(src):
                copy_tree(src, os.path.join(dst, sub))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    web = os.path.join(dst, "web")
    backup = os.path.join(dst, "pracovni", "zaloha_web_" + stamp)
    changed = copy_tree(os.path.join(SKILL, "template", "web"), web, backup if os.path.isdir(web) else None)
    tools = os.path.join(dst, "tools")
    os.makedirs(tools, exist_ok=True)
    # nástroje vždy aktualizovat – ale ty, které se v projektu upravily, nejdřív zazálohovat (jinak by se úprava ztratila);
    # .skill_nastroje.json pamatuje otisky naposledy nainstalovaných verzí, podle nich se upravené pozná
    record = os.path.join(dst, ".skill_nastroje.json")
    known = json.load(open(record, encoding="utf-8")) if os.path.exists(record) else None
    tools_backup = os.path.join(dst, "pracovni", "zaloha_nastroje_" + stamp)
    edited, prints = [], {}
    for f in sorted(os.listdir(os.path.join(SKILL, "tools"))):
        if f.endswith((".py", ".sh")) and f != "novy_projekt.py":
            new, out = os.path.join(SKILL, "tools", f), os.path.join(tools, f)
            if os.path.isfile(out) and not os.path.islink(out) and not filecmp.cmp(new, out, shallow=False) \
                    and (known is None or known.get(f) != fingerprint(out)):
                os.makedirs(tools_backup, exist_ok=True)
                shutil.copy2(out, os.path.join(tools_backup, f))
                edited.append(f)
            copy(new, out)
            if f.endswith(".sh"):   # skill naklonovaný na Windows (core.autocrlf) má CRLF – Git Bash by skript nespustil
                data = open(out, "rb").read()
                if b"\r\n" in data:
                    open(out, "wb").write(data.replace(b"\r\n", b"\n"))
            prints[f] = fingerprint(out)
    with open(record, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(prints, fh, indent=1, sort_keys=True)
    for d in ("vyrezy", "zdroje", "dokumenty", "pracovni"):
        os.makedirs(os.path.join(dst, d), exist_ok=True)
    os.makedirs(os.path.join(dst, ".claude"), exist_ok=True)
    # pomocníci (.claude/agents/ctenar-matrik.md – Sonnet, kontaktní listy): jako web – liší-li se, záloha a nová verze
    agents = os.path.join(dst, ".claude", "agents")
    agents_backup = os.path.join(dst, "pracovni", "zaloha_pomocnici_" + stamp)
    changed_agents = copy_tree(os.path.join(SKILL, "template", ".claude", "agents"), agents,
                               agents_backup if os.path.isdir(agents) else None)
    # návod ke čtení matrik pro pomocníka (skill sám nenačítá): kopie reference/matriky.md, při aktualizaci vždy nová
    guide = os.path.join(dst, ".claude", "cteni_matrik.md")
    text = ("<!-- Kopie reference/matriky.md ze skillu rodokmen – při aktualizaci projektu se přepíše, neupravuj ji."
            " Odkazy na portaly.md, playbook.md, data.md a SKILL.md míří do skillu. -->\n\n"
            + open(os.path.join(SKILL, "reference", "matriky.md"), encoding="utf-8").read())
    if os.path.lexists(guide):
        if os.path.islink(guide):
            os.remove(guide)
        elif open(guide, encoding="utf-8").read() != text:
            os.makedirs(agents_backup, exist_ok=True)
            shutil.copy2(guide, os.path.join(agents_backup, "cteni_matrik.md"))
    with open(guide, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    gitignore = doplnit_gitignore(dst)
    for name in ("CLAUDE.md", ".gitignore", ".gitattributes", "poznamky_pro_skill.md", os.path.join(".claude", "launch.json")):
        out = os.path.join(dst, name)
        if not os.path.lexists(out):
            copy(os.path.join(SKILL, "template", name), out)
    with open(os.path.join(dst, ".skill_verze"), "w", encoding="utf-8") as f:   # SKILL.md podle něj nabídne aktualizaci
        f.write(open(os.path.join(SKILL, "VERZE"), encoding="utf-8").read())
    print("Projekt připraven:", dst)
    if changed_agents:
        print(f"Pomocníci aktualizováni ({', '.join(changed_agents)}); původní verze v {agents_backup}.")
    if gitignore:
        print(".gitignore doplněn o: " + ", ".join(gitignore) + " (už uložené soubory z nich vyndá `git rm -r --cached <cesta>` + commit)")
    if changed:
        print(f"Web aktualizován na novou šablonu ({len(changed)} souborů). Původní verze jsou v {backup}:")
        for f in changed:
            print("  web/" + f)
        print("Pokud jste vzhled webu upravovali, převezměte úpravy ze zálohy. Pak `npm install` a `npm run data` ve web/.")
    if edited:
        print(f"Nástroje, které se v projektu lišily ({len(edited)}), nová verze přepsala. Původní jsou v {tools_backup}:")
        for f in edited:
            print("  tools/" + f)
        print("Úpravy z nich převezměte do nových verzí (porovnejte soubory), jinak se ztratí."
              + ("" if known is not None else " Projekt zatím neměl záznam verzí nástrojů,"
                 " takže v seznamu můžou být i neupravené nástroje starší verze skillu."))


if __name__ == "__main__":
    main()
