#!/usr/bin/env python3
"""Předci a rody v data/osoby.json: načtení, zápis a převod ze starého data/osoby.py.

Používají ho export_web, fan_chart, kontrola, napady a ged_import. Sekce souboru: P (předci podle Kekulého
čísel), LINES (rody 8–15), SIDE, ISSUES, HYPOTEZY, SAME – formát v reference/data.md ve skillu.

Převod starého projektu (osoby.py → osoby.json, původní soubor do pracovni/osoby_puvodni.py):
  python3 -I tools/nacti_osoby.py prevod
Dělá ho i novy_projekt.py při aktualizaci projektu. Starý soubor se při převodu nespouští: rozebere se (ast)
a přijmou se jen přiřazení hodnot.
"""
import ast, json, os, shutil, sys

SEKCE = ("P", "LINES", "SIDE", "ISSUES", "HYPOTEZY", "SAME")
POPIS = ("Předci podle Kekulého čísel (1 = výchozí osoba, otec osoby n = 2n, matka = 2n+1), rody LINES, boční "
         "příbuzní SIDE, otázky ISSUES, HYPOTEZY, SAME. Formát: reference/data.md ve skillu rodokmen.")


def _cislo(k):
    """Kekulého číslo z klíče JSON („8“ → 8); co není číslo, nechá být (kontrola.py to nahlásí)."""
    return int(k) if isinstance(k, str) and k.isdigit() else k


def _poradi(k):
    """Řazení klíčů v souboru: čísla podle velikosti (i jako „8“ z JSON), ostatní za nimi."""
    c = _cislo(k)
    return (0, c, "") if isinstance(c, int) else (1, 0, str(c))


def nacti_osoby(data_dir):
    """Vrátí slovník sekcí z data/osoby.json; klíče P, LINES a SAME (i hodnoty SAME) jako čísla."""
    path = os.path.join(data_dir, "osoby.json")
    if not os.path.exists(path) and os.path.exists(os.path.join(data_dir, "osoby.py")):
        raise ValueError("data/osoby.py je starý formát – převeďte ho: python3 -I tools/nacti_osoby.py prevod")
    with open(path, encoding="utf-8-sig") as f:   # -sig: soubor s BOM (Windows PowerShell) se taky načte
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"data/osoby.json, řádek {e.lineno}, sloupec {e.colno}: {e.msg}") from None
    data = {k: v for k, v in data.items() if not k.startswith("_")}
    for name in ("P", "LINES", "SAME"):
        if isinstance(data.get(name), dict):
            data[name] = {_cislo(k): v for k, v in data[name].items()}
    if isinstance(data.get("SAME"), dict):
        data["SAME"] = {k: _cislo(v) if isinstance(v, str) else v for k, v in data["SAME"].items()}
    return data


def format_osoby(data):
    """Text osoby.json: co osoba (rod, příbuzný, otázka), to jeden řádek – dobře se v tom hledá i upravuje."""
    one = lambda v: json.dumps(v, ensure_ascii=False)
    parts = [f' "_popis": {one(data.get("_popis", POPIS))}']
    for name in SEKCE + tuple(sorted(k for k in data if k not in SEKCE and not k.startswith("_"))):
        v = data.get(name, [] if name in ("SIDE", "ISSUES", "HYPOTEZY") else {})
        if not isinstance(v, (dict, list)):
            parts.append(f" {one(name)}: {one(v)}")
        elif isinstance(v, dict):
            rows = [f"  {one(str(k))}: {one(x)}" for k, x in sorted(v.items(), key=lambda kv: _poradi(kv[0]))]
            parts.append(f' "{name}": {{' + ("\n" + ",\n".join(rows) + "\n }" if rows else "}"))
        else:
            rows = [f"  {one(x)}" for x in v]
            parts.append(f' "{name}": [' + ("\n" + ",\n".join(rows) + "\n ]" if rows else "]"))
    return "{\n" + ",\n".join(parts) + "\n}\n"


def uloz_osoby(data_dir, data):
    path = os.path.join(data_dir, "osoby.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(format_osoby(data))
    os.replace(tmp, path)


# --- převod ze starého formátu (data/osoby.py) – soubor se nespouští, jen rozebere ---

def _ukazka(node):
    """Začátek kódu pro chybovou hlášku (jen první řádek)."""
    return ast.unparse(node).splitlines()[0][:60]


def _value(node):
    if isinstance(node, ast.Constant) and not isinstance(node.value, bytes):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)) \
            and isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, (int, float)):
        return -node.operand.value if isinstance(node.op, ast.USub) else node.operand.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):   # "dlouhý " + "text"
        a, b = _value(node.left), _value(node.right)
        if isinstance(a, str) and isinstance(b, str):
            return a + b
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_value(v) for v in node.elts]
    if isinstance(node, ast.Dict) and None not in node.keys:
        return {_value(k): _value(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict" \
            and not node.args and all(k.arg for k in node.keywords):
        return {k.arg: _value(k.value) for k in node.keywords}
    raise ValueError(f"řádek {node.lineno}: '{_ukazka(node)}' není hodnota – převod bere jen řetězce, čísla, "
                     "seznamy, n-tice, slovníky a dict(…)")


def nacti_stare_osoby(path):
    """Sekce ze starého osoby.py (P = {…}, P[16] = dict(…) …) bez spuštění kódu."""
    with open(path, encoding="utf-8-sig") as f:
        tree = ast.parse(f.read(), filename=path)
    ns = {}
    for st in tree.body:
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant):   # docstring
            continue
        if isinstance(st, ast.Assign) and len(st.targets) == 1:
            t = st.targets[0]
            if isinstance(t, ast.Name):                                          # P = {…}
                ns[t.id] = _value(st.value)
                continue
            if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and isinstance(ns.get(t.value.id), dict):
                ns[t.value.id][_value(t.slice)] = _value(st.value)               # P[16] = dict(…)
                continue
        raise ValueError(f"řádek {st.lineno}: '{_ukazka(st)}' – převod bere jen přiřazení hodnot "
                         "(P = {…}, LINES = {…} …); tento řádek přepište do osoby.json ručně")
    return ns


def prevod(root):
    """data/osoby.py → data/osoby.json, původní soubor do pracovni/osoby_puvodni.py. Vrací True, když převáděl."""
    data_dir = os.path.join(root, "data")
    old, new = os.path.join(data_dir, "osoby.py"), os.path.join(data_dir, "osoby.json")
    if not os.path.exists(old) or os.path.exists(new):
        return False
    uloz_osoby(data_dir, nacti_stare_osoby(old))   # neznámé proměnné zůstanou jako sekce navíc, nahlásí je kontrola.py
    os.makedirs(os.path.join(root, "pracovni"), exist_ok=True)
    shutil.move(old, os.path.join(root, "pracovni", "osoby_puvodni.py"))
    return True


if __name__ == "__main__":
    if sys.argv[1:] != ["prevod"]:
        sys.exit(__doc__)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print("data/osoby.py převedeno na data/osoby.json (původní soubor: pracovni/osoby_puvodni.py)" if prevod(root)
          else "Není co převádět (chybí data/osoby.py, nebo už existuje data/osoby.json).")
