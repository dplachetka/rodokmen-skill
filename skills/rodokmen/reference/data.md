# Formát dat projektu

Všechna data jsou v `data/`. Web se z nich generuje (`npm run data`), nikdy needituj `web/src/data/site.json` ručně.
Po změnách spusť `python3 -I tools/kontrola.py`. Ukázku vyplněných dat má `SKILL_DIR/template/ukazka/`.
Položky do `zaznamy`, `svazky`, `prepisy`, `zvyrazneni`, `mista` a `dokumenty` přidávej a měň přes `python3 -I tools/zapis.py`
(zachová formát souboru, viz SKILL.md); `osoby.json` nástrojem pro úpravu souborů. Hledat v datech:
`python3 -I tools/hledej.py <text>` (osobu vypíše celou, nevadí diakritika).

## `osoby.json` – předci
Kekulého čísla: 1 = výchozí osoba, otec osoby n = 2n, matka = 2n+1.
| číslo | kdo |
|---|---|
| 1 | výchozí osoba (u ženy `"sex": "F"`) |
| 2, 3 | otec, matka |
| 4–7 | prarodiče (4, 5 otcovi rodiče; 6, 7 matčini) |
| 8–15 | pradědečci a prababičky = **8 rodů** (`LINES`) |
| 16–31, 32–63 … | každá další generace dvojnásobek |

Otec předka 22 je 44, matka 45; dítě předka 45 je 22 (45 // 2). Muži mají sudá čísla.

Soubor má sekce `P`, `LINES`, `SIDE`, `ISSUES`, `HYPOTEZY`, `SAME`; je to běžný JSON odsazený po jedné mezeře
jako ostatní datové soubory:
```json
{
 "_popis": "…",
 "P": {
  "8": {
   "n": "Jan Novák",
   "y": "1890–1944",
   "st": "doc",
   "f": [
    "* 14. 2. 1890 Holice čp. 112",
    "kovář",
    "× 20. 6. 1919 Holice Josefa Pokorná",
    "† 1944 Holice"
   ],
   "r": [
    "holice_krest_jan_novak_1890",
    "holice_snatek_jan_novak_josefa_pokorna_1919"
   ],
   "note": "Proč nejistota / rozpor / odkud údaj",
   "sour": "částečně"
  },
  "9": {
   "n": "Josefa Pokorná",
   "y": "* 1895",
   "st": "doc",
   "f": [
    "…"
   ],
   "r": [
    "…"
   ]
  },
  "33": {
   "n": "otec neuveden",
   "st": "unk",
   "f": [],
   "note": "Nemanželský syn; otec v matrice není."
  }
 },
 "LINES": {
  "8": [
   "Novákové",
   "Kováři z Holic…"
  ]
 },
 "SIDE": [
  {
   "k": 16,
   "n": "Josef Novák",
   "v": "bratr",
   "y": "1865–1920",
   "st": "doc",
   "f": [
    "* 3. 2. 1865 Holice čp. 112",
    "kovář",
    "† 1920 Holice"
   ],
   "t": "Převzal kovárnu po otci.",
   "r": [
    "klic_zapisu"
   ]
  }
 ],
 "ISSUES": [
  [
   "Kdy se narodil Jan Novák?",
   "Otevřené: rodina říká 1850, v Holicích 1848–1852 nenalezen."
  ]
 ],
 "HYPOTEZY": [
  {
   "rod": 8,
   "nadpis": "Hypotéza: Novákové z Lhoty",
   "text": "…",
   "polozky": [
    [
     "Jan Novák",
     "kmotr 1681…"
    ]
   ],
   "zaznamy": [
    "klic"
   ]
  }
 ],
 "SAME": {
  "350": 140
 }
}
```
- Je to JSON: texty v dvojitých uvozovkách (uvozovka v textu `\"`, raději ale „české“), čárka mezi položkami, za
  poslední ne; čísla osob jako klíče v uvozovkách. Komentáře JSON nemá – poznámky patří do `note`. Po úpravě
  `kontrola.py` ukáže případnou chybu i s řádkem. Klíče začínající `_` nástroje přeskakují.
- `n` jméno (ženy rodným příjmením, u nejistého čtení „(?)“), `y` roky pro přehledy (`"* 1895"`, `"1890–1944"`,
  `"asi 1720–1785"`, `"1680 – před 1740"`, `"† 1940"` když známe jen úmrtí; nic nevíme → `""`).
- `f` fakta: začínají `*` (narození), `×` (sňatek), `†` (úmrtí) nebo jsou volný text (řemeslo, bydliště).
  Názvy obcí ve faktech používá mapa (`mista.json` → `re`).
- `r` klíče zápisů ze `zaznamy.json`. `st` viz `matriky.md`: `doc` přečteno v matrice, `prob` pravděpodobné,
  `fam` od rodiny (i strom, který si rodina vede sama, např. GEDCOM z jejího MyHeritage), `mh` cizí strom z internetu, `unk`.
- `note` proč je údaj nejistý, rozpory, odkud se vzal. Žijící lidé: jen jméno a rok narození, `"note": "Žijící – údaje jen základní."`
- `sour` (volitelné) stav hledání sourozenců předka: `"hotovo"` = všichni dohledáni, `"částečně"`; chybí = zatím nehledáno –
  stromový graf (`/strom/`) u ostatních ukazuje „sourozenci nehledáni“ jako připomínku, co dohledat.
- `LINES` – jen čísla 8–15: `[název rodu, jedna věta o rodu]`; název rodu = příjmení v množném čísle.
- `SIDE` – sourozenci, další příbuzní i nepříbuzní lidé kolem rodiny: `k` = číslo předka, ke kterému patří, `n` jméno
  (bez let), `r` klíče zápisů a stejná pole jako u předků: `y` roky (`"* 1931"`, `"1893–1960"`), `st` stav doložení,
  `f` fakta (`*` `×` `†` s datem a místem, povolání), `t` volný text. Všechno kromě `k` a `n` je volitelné.
- `v` vztah k předkovi rozhoduje, kde je člověk na webu (stránka rodiny, osoby i strom):
  | `v` | skupina na webu |
  |---|---|
  | `bratr`, `sestra` (u záznamu za víc lidí `sourozenci`, `bratři`, `sestry`) | Sourozenci (na stránce rodiny pod „Děti“) |
  | `manžel`, `manželka`, `syn`, `dcera`, `strýc`, `bratranec`… (cokoli jiného) | Další příbuzní |
  | `učeň`, `tovaryš`, `čeledín`, `služebná`, `podruh`, `nájemník`, `soused`, `kmotr`, `svědek`… nebo `nepříbuzný` | Lidé kolem rodiny |
  | chybí | Vztah zatím neuveden (`kontrola.py` to hlásí) |
  Kmotr nebo svědek může být i příbuzný – pak patří vztah (`strýc`), role do textu. Web ukazuje kartu s roky,
  vztahem, stavem, fakty a zápisy; stromový graf kreslí lidi vedle předka. Údaje ze zápisu patří do `f`, ne do textu.
  Žijící (narození před méně než 100 lety, žádné †): jen jméno a rok narození – `kontrola.py` hlásí `ŽIJÍCÍ?`.
- **Příbuzné zapisuj tak, aby šli později převést na osoby s rodiči** (číslo předka `k` a vztah dají rodiče):
  - sourozenec vždy `bratr` nebo `sestra`, ne `sourozenec`; jeden záznam na člověka (`sourozenci` jen, když víš jen počet),
  - nejistý vztah s „(?)“: `"bratr (?)"`, důvod do `t`,
  - nevlastní sourozenec se společným rodičem: `"nevlastní bratr (stejná matka)"`, `"nevlastní sestra (stejný otec)"`,
  - partner a děti sourozence jako fakta v `f`: `"× 12. 5. 1890 Ostřetín Karel Hrubý"`, `"syn Jaroslav Hrubý * 1920 Ostřetín"`.
- Starší tvar (roky ve jméně „Josef Novák (1865–1920)“, vztah jen v textu) převede
  `python3 -I tools/nacti_osoby.py sourozenci` (`--nanecisto` jen ukáže změny): roky do `y`, vztah z prvního slova
  textu do `v` („Bratr …“, „Učeň …“, „Sourozenci Jana …“; text s „Nepříbuzný“ → `nepříbuzný`), text zůstává celý.
  Kmotra a svědka nedoplní – rozhodni s uživatelem.
  Fakta z textu pak přepiš do `f` ručně.
- `ISSUES` – dvojice `[otázka, odpověď]`, odpověď začíná „Vyřešeno: …“ (na webu se skryje), „Hypotéza: …“ nebo
  „Otevřené: …“ → stránka „Co hledáme“. Jde na web – nepiš sem citlivé věci (příčiny úmrtí, rodinné spory) bez souhlasu.
- `HYPOTEZY` – hypotézy o původu rodu nad rámec doložené linie → stránka rodu (`rod` = číslo 8–15).
- `SAME` – předek, který je v rodokmenu dvakrát (alias → hlavní číslo; alias v `P` může mít `"f": ["TÁŽ OSOBA jako 140"]`).
- Starší projekt má místo toho `data/osoby.py`: převede ho `python3 -I tools/nacti_osoby.py prevod` (dělá to i
  `novy_projekt.py` při aktualizaci nástrojů). Starý soubor se při tom nespouští, odloží se do `pracovni/osoby_puvodni.py`.

## `zaznamy.json` – zápisy
```json
[{"klic": "holice_krest_jan_novak_1890", "svazek": "1a0b2337", "snimek": 57, "druh": "N",
  "datum": "14. 2. 1890", "nazev": "Křest Jana Nováka",
  "shrnuti": "Jan, syn Václava Nováka, kováře v Holicích čp. 112, a Barbory roz. Malé z Ostřetína.",
  "odkaz": "https://aron.vychodoceskearchivy.cz/apu/…/dao/…/file/…"}]
```
- `klic`: malá písmena bez diakritiky, `obec_druh_kdo_rok` (druh: krest, snatek, umrti, index, scitani…). Je to i název obrázku.
- `druh`: N, O, Z, I (index/rejstřík), S (sčítání), J (jiný pramen).
- `datum` jako v češtině („14. 2. 1890“, „3/1867“, „1797“) – web podle něj řadí.

## `svazky.json`
`{"1a0b2337": {"archiv": "SOA Zámrsk – Sbírka matrik…", "portal": "ARON", "svazek": "N Holice 1880–1900, sign. …",
"popis": "obce", "url": "odkaz na svazek"}}` – u ARON zapisuje `aron_img.py <apu> svazek`.

## `prepisy.json`
`{"<klic>": {"orig": "[Datum] 14. února 1890\n[Dům] 112\n[Otec] …", "cs": "Český překlad celou větou…"}}`
- `orig` věrný přepis po sloupcích, `[Název sloupce]` v hranatých závorkách, nejisté „(?)“, nečitelné „[…]“, zkratky ponechat.
- `cs` srozumitelný překlad pro rodinu; vysvětli staré pojmy (domkář, podruh).

## `zvyrazneni.json`
`{"<klic>": {"boxes": [[x0, y0, x1, y1]], "status": "ok", "note": ""}}` – zlomky šířky/výšky obrázku `vyrezy/<klic>.jpg`.
Zapisuje `ramecek.py`. Rámeček má obepnout celý čtený zápis (ne jen jméno).

## `mista.json`
`{"Holice": {"re": "Holic", "dotaz": "Holice, Česko", "lat": 50.066, "lon": 15.986}}` – `re` je regulární výraz hledaný
ve faktech osob (kmen slova, aby sedělo skloňování: „Holic“ najde Holice i v Holicích). Spravuje `mista.py`.
Pozor na kolize (Hradec Králové × Nový Hradec Králové – použij `(?<!Nový )Hradec`; krátká jména jako `\bBuku?\b`).
Hypotéza: `"hypoteza": true, "rod": 8`. Když OpenStreetMap obec nenajde („Žár“, malé osady), zkus třetí parametr – dotaz: `mista.py pridej "Žár" "Žár" "Žár, Zdíkov, okres Prachatice"`
nebo dotaz s větší obcí či okresem. U **víceznačných názvů** (Podolí, Dub, Lhota) vezme OpenStreetMap kteroukoli ves
(„Podolí, Česko“ = Podolí u Brna) – v posledním sloupci výpisu zkontroluj okres a dej dotaz se sousední obcí
(`mista.py pridej "Podolí" "Podol" "Podolí, Odlochovice"`). Místopis nejlíp zná rodina – když si nejsi jistý, zeptej se.

## `dokumenty.json` – rodinné fotky a dokumenty na webu
`[{"img": "foto_svatba_1919", "popis": "Svatba Jana a Josefy, Holice 1919.", "osoby": [8, 9]}]`
Obrázek ulož přes `vyrez.py dokumenty/<sken>.jpg foto_svatba_1919` (vznikne `vyrezy/` i `zdroje/`).

## `web.json` – nastavení webu
Viz `web.md`.

## Markdown poznámky
- `research_log.md` – tabulka `| # | datum | zdroj | rozsah | hledáno | výsledek | citace |`, nové řádky na konec, i negativní.
  Web ji zobrazuje jako „Výzkumný deník“.
- `zajimavosti.md` – `## Nadpis` + text, odkazy `[Jméno](/osoba/<slug>/)`.
- `pribeh.md` – „Příběh <hlavního rodu>“: frontmatter `title`, `lead` + kapitoly `##`; když soubor neexistuje,
  položka menu se skryje. Jak psát: `pribehy.md`.
- Poznámky pro Clauda v markdownu piš jako `<!-- … -->` – na web nejdou.
- `archivni_dotazy.md`, `udaje_od_rodiny.md` – volný text.

## Odkazy na osoby (slug)
Slug = jméno bez diakritiky + rok, např. `jan-novak-1890`; při kolizi přidá číslo osoby. Přesné slugy po `npm run data`
v `web/src/data/site.json` (`people`). Při přejmenování osoby se slug změní – oprav odkazy v textech.
