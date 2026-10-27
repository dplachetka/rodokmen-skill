# Portály archivů a jak z nich dostat snímky

Matriky jsou online u osmi státních archivů – podle toho, **kde předci žili** (dnešní kraje zhruba odpovídají):

| Archiv | Oblast | Portál s matrikami | Vyzkoušeno se skillem |
|---|---|---|---|
| SOA Zámrsk | východní Čechy (Hradecký a Pardubický kraj) | ARON – aron.vychodoceskearchivy.cz | **ano – hotové nástroje** |
| SOA Praha | střední Čechy | eBadatelna – ebadatelna.soapraha.cz | **ano – nástroj `ebadatelna.py`** (i urbáře a gruntovní knihy) |
| SOA Plzeň | západní Čechy | Porta fontium – portafontium.eu | **ano – nástroj `portafontium.py`** |
| SOA Třeboň | jižní Čechy | digi.ceskearchivy.cz | **ano – nástroj `trebon.py`** |
| SOA Litoměřice | severní Čechy | Digitální badatelna – digi.soalitomerice.cz | **částečně – `soal_zoomify.py`** (knihu najdi v prohlížeči; při výpadku FamilySearch) |
| AHMP | hl. m. Praha | katalog.ahmp.cz (Pragapublica) | **ano – `ahmp_search.sh`, `ahmp_scan.py`** |
| MZA Brno | jižní Morava, Vysočina z části | Acta Publica – www.mza.cz/actapublica | částečně – v prohlížeči (postup níže) |
| ZA Opava | severní Morava a Slezsko, Olomoucko a Litovelsko | Digitální badatelna – digi.archives.cz/da/ | **částečně – `soal_zoomify.py`** (jen s prohlížečem, CAPTCHU řeší uživatel) |
| Národní archiv | židovské matriky (HBMa), soupisy; pražské policejní přihlášky 1850–1914 | badatelna.eu; digi.nacr.cz/prihlasky2 | přihlášky **ano – `policie_prihlasky.py`** |

Adresy u nevyzkoušených portálů ověř při prvním použití (portály se mění). Pro pohraničí a mimo ČR viz `playbook.md` §2
(Matricula pro Rakousko/Německo, Geneteka pro Polsko, FamilySearch pro Slovensko) a níže.

## ARON (SOA Zámrsk) – hotové nástroje
- **Hledání svazků:** `python3 -I tools/aron_search.py "Holice"` → řádky `apu_id | signatura, roky | druh, obce`.
  Popis obsahuje druh knihy (NAROZENÝCH / ODDANÝCH / ZEMŘELÝCH, index) a všechny obce farnosti.
- **Informace o svazku:** `python3 -I tools/aron_img.py <apu_id> info` → název a počet snímků.
- **Stažení snímku:** `python3 -I tools/aron_img.py <apu_id> <snímek> 1 pracovni/holice_n_57.jpg`
  (úroveň 1 = poloviční rozlišení – stačí na orientaci; 0 = plné rozlišení – na čtení a výřez).
  Jen část stránky v plném rozlišení: `… <snímek> 0 pracovni/detail.jpg 0.0,0.4,1.0,0.7`.
- **Odkaz na snímek** (pole `odkaz` v `zaznamy.json`): `python3 -I tools/aron_img.py <apu_id> link <snímek>`.
- **Svazek do dat:** `python3 -I tools/aron_img.py <apu_id> svazek` (klíč = prvních 8 znaků apu_id → pole `svazek` v zápisu).
- **Celé svazky ručně** (když ARON vypadává, nebo se bude číst hodně snímků): uživatel stáhne svazek tlačítkem v prohlížeči
  → složka `CZ_<archiv>_<fond>_<kód>_sign-<signatura>/` se soubory `…_00001_…jpg` = snímek 1 (u sčítání lidu `…_00010_…`
  = snímek 1, tedy číslo souboru / 10). Ať ji uloží do `dokumenty/` (`.gitignore` ji vynechá) a čti z disku – spolehlivější
  a rychlejší než stahování po snímcích; `vyrez.py` bere soubor přímo. Odkaz (`link`) a `svazek` doplň, až ARON odpovídá.
  Co má uživatel stáhnout, veď v `data/STAV.md` jako seznam „Ke stažení“ s odkazy na svazky; stažené a ještě nepřečtené
  svazky v tabulce „Na disku, ale nepřečteno“ (co v nich hledat) – ať se na ně po pár sezeních nezapomene.
- V ARON jsou i další fondy (sčítání lidu, některé gruntovní knihy, kroniky) – `aron_search.py "Obec" "název fondu"`.
- Stejnojmenných obcí bývá víc (Vinice u Hořic × Vinice u Velké Jesenice). Výsledky jsou seřazené podle farnosti;
  zúžit jde víc slovy oddělenými čárkou, která musí být v popisu všechna: `aron_search.py "Vinice,Hořice"`
  (nebo hledej sousední obec či farní obec).
- U starých far hledej nejdřív **souhrnné indexy** (popis „index NAROZENÝCH…“ přes mnoho let), často sahají do 17. století.
- Obec nenalezena? Zkus název **bez přívlastku** („Lhota“ místo „Horní Lhota“) a starý název. Starší matriky
  (před ~1784) bývají ve faře sousedního města; indexy fary mají oddíly po vesnicích
  („Copulati Gross Lhota“).
- Ber ohled na server: nástrojem (`aron_img.py`) stahuj jen snímky, které čteš – celý svazek po snímcích nestahuj.
  Potřebuješ-li ho celý, ať ho uživatel stáhne tlačítkem v prohlížeči (viz „Celé svazky ručně“ výše).

## SOA Třeboň (digi.ceskearchivy.cz) – `tools/trebon.py`, bez prohlížeče
- `trebon.py misto "Obec"` → id místa. Diakritiku a mezery nástroj odstraní sám (portál zná jen „RatiborskeHory“).
  Portál vrátí vždy jen jedno místo – **zkontroluj vypsaný název a okres**: u stejnojmenných obcí jinou (Buk → Bukovka),
  u měst i okres nebo synagogu (Jindřichův Hradec → okres 1949–1960). Správné id pak najdi na portálu a pracuj s ním.
  Malé osady portál jako místo nezná vůbec (Malá Chyška) – hledej farní nebo sousední obec (Chyšky) a osadu v popisu knih.
  Občasná chyba 500 bývá výpadek portálu – nástroj zkouší znovu; když trvá, zkus to později.
- `trebon.py svazky <id|"Obec">` → knihy místa (id knihy, druh, roky, obce).
- `trebon.py rejstrik <id_knihy> <písmeno>` → **dobrovolnický jmenný rejstřík** knihy se snímkem, obrovská úspora.
  Ne každá kniha ho má; prázdný výsledek = rejstřík chybí, ne „osoba tam není“.
- `trebon.py snimek <id_knihy> <snímek> pracovni/x.jpg [nahled]`, `trebon.py svazek <id_knihy>` (do `svazky.json`).
- Trvalý odkaz: `https://digi.ceskearchivy.cz/<id_knihy>/<snímek>`.
- Některé fary mají knihy po vesnicích, které nejsou v seznamu svazků místa (Vacov → Žár) – hledej podle titulků knih fary.
- **Civilní matriky (1920–1945) lidí bez vyznání** jsou v knihách okresních úřadů (např. Tábor, kniha 12304) a mají
  dobrovolnický rejstřík (`trebon.py rejstrik 12304 N`). Dobrá cesta, když farní matrika mlčí. V `svazky "Obec"`
  se neukážou (patří okresu, ne obci) – id knihy najdi na portálu.

## SOA Plzeň (Porta fontium, portafontium.eu) – `tools/portafontium.py`, bez prohlížeče
- `portafontium.py fara <fara>` → knihy fary: kniha | obce | roky a druhy (`*` N, `oo` O, `+` Z, `i` index) | popis.
  `<fara>` je název římskokatolické fary („Dolní Bělá“, „Mýto“ – diakritiku nástroj odstraní) nebo přímo část
  její adresy (`dolni-bela` =
  `…/contents/register/soap-pn/cirkev-rimskokatolicka/dolni-bela`). Obec → faru nástroj nehledá: faru zjisti ve vyhledávání
  matrik na portálu (pole Místo, v prohlížeči) nebo v popisech knih okolních far. Bez prohlížeče: stránka
  `https://www.portafontium.eu/searching/register?search_api_views_fulltext_1=<obec>` vypíše odkazy
  `/register/soap-pn/<kniha>` – `<kniha>` (např. `kdyne-29`) rovnou použij v `portafontium.py info`.
- `portafontium.py info <kniha>` (`dolni-bela-17`) → signatura, druh, text desky a **obsah** – u knih psaných po vesnicích
  vypíše, na kterých foliích je která obec („Ves X z let 1862–1901 = fol. 121–200“).
- `portafontium.py snimek <kniha> <snímek> pracovni/x.jpg [nahled] [x0,y0,x1,y1]` → celá stránka v plném rozlišení jedním
  požadavkem (IIIF), `nahled` = 1/4. Číslo snímku = pořadí náhledu v prohlížeči; soubory nesou číslo folia
  (`dolni-bela-17_0951` = fol. 95), takže u knih se souvislou foliací je **snímek ≈ folio**.
- `link <kniha> <snímek>` → trvalý odkaz, `svazek <kniha>` → `svazky.json` (klíč `pf_<kniha>`).
- Bez prohlížečového User-Agentu portál vrací 403 (nástroj ho posílá). Jmenné hledání portál nemá – indexy jsou jen uvnitř knih
  (`*i`, `ooi`, `+i` v seznamu knih fary).

## SOA Praha (eBadatelna, ebadatelna.soapraha.cz) – `tools/ebadatelna.py`, bez prohlížeče
- `ebadatelna.py hledat "Obec"` → celé názvy lokalit („Lhota - obec X - okres Y“); `matriky "Obec"` (nebo celý název)
  → matrikaId | kniha | druh | roky | fara | počet snímků. U stejnojmenných obcí vypíše možnosti.
- `ebadatelna.py info <matrikaId>` → obsah knihy včetně **rozvržení stran po vesnicích** (např. „1–48 Ves A, 49–82 Ves B,
  1–30 Ves C …“ – každá ves může mít vlastní stránkování) – u takových knih neodhaduj snímek podle roku, ale podle stran
  dané vsi (číslo strany je nahoře na snímku). Takové knihy bývají řazené po vsích, ne chronologicky – je-li rejstřík,
  začni jím.
- `ebadatelna.py snimek <matrikaId> <snímek> pracovni/x.jpg [nahled] [x0,y0,x1,y1]`; `link`, `svazek` (klíč `ebad_<id>`).
- **Archiválie** (urbáře, gruntovní a pozemkové knihy velkostatků – most přes 17. století): `a-info <archivalieId>`,
  `a-snimek`, `a-link`, `a-svazek` (klíč `ebad_a_<id>`). Archiválii nástroj nehledá – najdi ji na portálu v prohlížeči;
  id je v adrese `…/pages/ArchivaliePage/archivalieId/<id>`.
- Starší snímky bývají z mikrofilmu nebo silně vybledlé – čti se zvýšeným kontrastem:
  `magick x.jpg -colorspace Gray -contrast-stretch 2%x30% x_k.jpg` (výřez pak dělej z kontrastní verze a poznamenej to v přepisu).
- Portál dává vždy celý snímek (nedlaždicuje); náhled a výřez dělá nástroj po stažení přes ImageMagick (`magick`).
  Denní údržba kolem 4:44 (asi 2 minuty).
- **Celé svazky stáhnout nejde** (na rozdíl od ARONu) – jen `snimek` po jednom: nejdřív `nahled` na odhad roku, plné
  rozlišení jen u čtených snímků.
- Velmi vybledlé snímky (některé fary): pomohlo `magick x.jpg -colorspace Gray -level 45%,85% x_k.jpg` – barevné `-level`
  dává zelenooranžové barvy, proto do šedi.
- **Sčítání lidu** jsou v sekci Archiválie (typ „Sčítací operáty“), ne u matrik, a jen pro část okresů. Formulář hledání je
  Wicket: hodnoty nastavené JavaScriptem se neuloží – vyplň je přes formulářové pole a klikni na „Hledat“. Pak `a-info` / `a-snimek` s id.

## AHMP Praha – `tools/ahmp_search.sh`, `tools/ahmp_scan.py`
- `bash tools/ahmp_search.sh "Smíchov"` → svazky Sbírky matrik: popis | farnost | (XID, id, počet snímků).
- `python3 -I tools/ahmp_scan.py <XID> <snímek> pracovni/x.jpg [1] [x0,y0,x1,y1]` → snímek (1 = poloviční rozlišení).
- Trvalý odkaz `https://katalog.ahmp.cz/pragapublica/permalink?xid=<XID>&scan=<N>`.
- Nový portál digi.ahmp.cz má ochranu proti robotům – nepoužívat. Pražské matriky 1890–1940 většinou **nemají rejstříky**
  a farností je mnoho – bez přesného data a farnosti (z úmrtí/sňatku nebo od rodiny) je hledání velmi drahé.

## SOA Litoměřice (severní Čechy) – `tools/soal_zoomify.py`
- **Dostupnost:** digitální badatelna `https://digi.soalitomerice.cz/digitalnibadatelna/` bývá i dny mimo provoz – vrací 404
  (výchozí stránka Tomcatu), nebo HTTP 200 s textem „Aplikace 'Vademecum' je z technických důvodů dočasně mimo provoz“.
  Kód 200 tedy neznamená „funguje“, podívej se na text. Mezitím zkus FamilySearch (níže – mnoho matrik i sčítání SOA
  Litoměřice tam je), jinak e-mail badatelna@soalitomerice.cz.
- Na vstupu je automatické ověření (asi 15 s „počítání“) → knihu a snímek hledej v prohlížeči.
- **Hledání:** do pole hledání psaní na souřadnice nefunguje; funguje JavaScript
  `patternTxt.value = "Obec"; form.querySelector('.inputSubmit').click()`. Typ „Matriky“ ale vyber kliknutím **před**
  hledáním, jinak se ztratí. Obec a období: ve „Specifickém filtru“ Datum od–do, počet na stránku 99 (select
  `pageRecords`; nastavení přes JavaScript se nemusí uložit – výsledky pak mají další stránky
  `vysledekList?page=2&actualRow=&actualUuid=`). Záznam bez „digi. sada“ není digitalizovaný.
- **Farnost podle vsi:** hledání názvu vsi s typem „Matriky“ vrátí knihy fary, kam ves patří, i s místními částmi
  („Pytlíkovský Mlýn“ → fara Jablonec u Mimoně). Stejnojmenné vsi rozliší okres v zápisu („hejtm. Mimoňské“).
  Rejstříky bývají samostatné svazky (např. „I-O“) a odkazují i na knihy, které online chybí.
- **Dva druhy záznamů matrik:**
  - *Starší digitalizace* (id záznamu s dvojtečkami, `09ddd7cea03b9b8d:…`): obrázky pod
    `…/CZ-214000010/NAD-856/dao/images/<složka>/<uuid>.jpg` (u jiných knih `…/matriky/<cesta>`) a **každý snímek má jiné
    uuid**. Adresu snímku n vrátí `fetch('/digitalnibadatelna/showZoomifySeparate?imageNumberSeparate=<n>&myEntityUuid='
    + encodeURIComponent(id))` – HTML s plnou adresou; id je v odkazu `vysledekDetail/<id>` v seznamu výsledků. Číslo
    za koncem knihy vrátí poslední snímek – tak zjistíš délku knihy. Mapu snímek → adresa si ukládej do
    `pracovni/<kniha>/mapa.json`, ať se na žádný snímek neptáš dvakrát. Rok najdi půlením (2–3 snímky), pak čti jen potřebný úsek.
  - *Knihy končící kolem 1949* (id 32 hex znaků, „sign. pův. …“) jsou **většinou jen v katalogu, bez snímků** („Záznam
    neobsahuje obrazové přílohy“). Když snímky mají, nese každý náhled id v atributu `hodnota` a adresu obrázku vrátí
    `fetch('/digitalnibadatelna/showZoomify/<id záznamu>/<id snímku>')`.
- **Past:** detail otevřený jen adresou `vysledekDetail/<id>` ukáže náhledy *jiné* knihy (podle pořadí v posledních
  výsledcích hledání) – přidej `?page=<pořadí ve výsledcích>` a zkontroluj signaturu.
- Snímky pak stahuj nástrojem: `python3 -I tools/soal_zoomify.py "<celá adresa obrázku>" 0 pracovni/x.jpg` (0 = plné
  rozlišení, 1 = poloviční). Adresu otevřeného snímku najdeš i v síťovém provozu (požadavek na `…/ImageProperties.xml`).
  Obrázkový server neomezuje a cookies nepotřebuje.
- **POZOR na blokování** (jen stránky aplikace – detail, prohlížení, `showZoomify…`; obrázky ne): po zhruba 100 rychlých
  požadavcích archiv zablokuje přístup na 30 minut. Za sezení prošlo bez blokace ~80 dotazů `showZoomifySeparate`
  s pauzou 0,8 s. V prohlížeči proto jen najdi knihu a adresy obrázků, pak už jen nástroj. Pomocníkům to napiš do zadání.
- **Čísla snímků i stran se liší od FamilySearch** (táž kniha: pag. 135 v SOA = pag. 168 na FamilySearch).
- **Kniha v seznamu matrik fary chybí** (např. narození vsi po 1860)? Nejspíš je mladší než 100 let a leží na matričním
  úřadě. Sňatky a úmrtí 1921–1949 bývají „v archivu“, ale nedigitalizované – navrhni rodinné doklady nebo žádost
  o výpis (`archivni_dotazy.md`).
- **Kroniky** (ne matriky) jsou pod `…/ximage/kroniky/zoomify/…/CZ-<kód SOkA>/kroniky/dao/images/…`; naskenovaná je jen
  menšina (v seznamu výsledků je poznáš podle odkazu na obrázky).
- **Sčítací operáty** jsou pod `…/ximage/operaty/…`. Tempo 1 dotaz za 6–10 s blokaci nevyvolalo (stovky dotazů za 2 h).
  Názvy snímků jsou časová UUID a sousední snímky mívají první hex pole o 2 vyšší – sondou na `…/TileGroup0/0-0-0.jpg`
  (načtením obrázku v prohlížeči, ne `fetch` – CORS) se dají najít bez dotazu na aplikaci. Dlouhé smyčky pouštěj
  v prohlížeči na pozadí; ve skrytém panelu `setTimeout` zpomalí – čekání přes Web Worker.
- **Adresáře ke stažení** (seznam na images.soalitomerice.cz/vademecum-proarchiv-resources/html/cs/seznam.html): okresní
  adresáře 1900–1940 jako ZIP (stovky MB) – dobré pro pohraničí, kde matriky po 1920 nejsou online. Většina je jen
  živnostenská; **seznam všech majitelů domů po obcích** mají jen „Adressbuch für den politischen Bezirk …“ – podívej se
  na název, než stáhneš stovky MB.

## ZA Opava (severní Morava, Slezsko, Olomoucko, Litovelsko) – `tools/soal_zoomify.py`
- Pozor na hranici: obce na Litovelsku a Olomoucku patří pod **ZA Opava**, ne pod MZA Brno.
- **Bez prohlížeče to nejde.** Badatelna `https://digi.archives.cz/da/` (stará adresa matriky.archives.cz jen přesměruje)
  má ochranu proti robotům – curl ani WebFetch se nedostanou ani na hledání. Potřebuješ připojený prohlížeč (Claude in
  Chrome – uživatel ho připojí příkazem `/chrome` – nebo Playwright); jinak ať knihu najde a snímky uloží uživatel.
  Úvodní ověření projde samo, ale hledání často skončí **CAPTCHou: tu vyřeší uživatel** v okně prohlížeče, ty nikdy.
- Hledej obec a vyfiltruj Matriky (ikona, potom znovu lupa). Hledání vrací i civilní matriky (u obce stovky svazků) –
  filtr „Datum od – do“ (podle začátku svazku, např. 1680–1873) nechá jen církevní. Knihy bývají řazené po obcích
  a na konci mají rejstřík. Vedle farních knih bývají i **druhopisy** („T“ v signatuře, viz `matriky.md`).
- **Seznam svazků a ID snímků si hned ulož** do `pracovni/<svazek>/` – relace po pár hodinách vyprší a výsledky
  hledání platí jen v ní. Na detailu svazku: entita `document.querySelector('[entityuuid]').getAttribute('entityuuid')`
  (u svazků uložených v jiném archivu nemá tvar UUID – nehledej ji regexem), ID snímků jsou hodnoty
  `select.getScanSelect option` (tvar „N%20uuid“). Snímek pak otevřeš kdykoli bez hledání:
  `/da/showZoomifySeparate?imageNumberSeparate=N&myEntityUuid=<entita>&myImageUuid=<uuid>`.
- Adresa obrázku: `fetch('/da/showZoomify/<id svazku z URL>/<část option.value za „%20“>')` vrátí HTML s cestou
  `…/images/<složka>/<uuid>.jpg`. Cesta se u svazků liší (`…/CZ-217000010/NAD-165/dao/images/…`, `…/zao/matriky/dao/images/…`)
  a přípona bývá i `.JPG` – nástroji dej vždy **celou adresu z HTML**:
  `python3 -I tools/soal_zoomify.py "<adresa>" 2 pracovni/x.jpg` (2 = čtvrtinové rozlišení na orientaci podle záhlaví
  stránek, 0 = plné jen u nalezeného zápisu). Obrázkový server images.archives.cz neomezuje a cookies nepotřebuje.
- **POZOR na blokování** (jen stránky aplikace, obrázky ne): rychlé dotazy → CAPTCHA, „operace vyhodnoceny jako
  nestandardní“ nebo „Access blocked“ na 30 minut; po desítkách dotazů za den vrací showZoomify „Server Exception“
  (denní limit – pokračuj až další den). Pauza 3–6 s mezi stránkami, dávky do ~80 stránek, žádné rychlé `fetch` hned
  po hledání a stránky výsledků neprocházej za sebou. Delší smyčku pusť v prohlížeči na pozadí, výsledky ukládej do
  `window` nebo `localStorage` a vyzvedávej po částech (nástroj pro JavaScript má limit asi 45 s). Pomocníkům to napiš do zadání.

## MZA Brno (jižní Morava, Acta Publica) – bez nástroje
- Portál `https://www.mza.cz/actapublica/`, bez přihlášení. Adresa actapublica.eu bývá za Cloudflare zablokovaná
  („Sorry, you have been blocked“ – podle IP, i v běžném prohlížeči); když blokuje i mza.cz, ať uživatel vypne VPN
  nebo zkusí jinou síť.
- Knihu najdi v prohlížeči podle obce nebo fary. Snímky jsou IIIF: adresu obrázku najdi v síťovém provozu a stáhni ji
  přes `curl` (Python dostane HTTP 426). Dál podle „Ostatní portály“ níže.

## Pražské policejní přihlášky 1850–1914 (Národní archiv) – `tools/policie_prihlasky.py`
- Karty pražských rodin: hlava rodiny, manželka s rokem a místem narození, děti s roky, adresy, někdy místo sňatku.
  Výborné, když rodina žila v Praze a nevíš farnost (pražské matriky nemají rejstříky).
- `python3 -I tools/policie_prihlasky.py Kolar [Jan] [1850] [1870]` – příjmení bez diakritiky (začátek jména), jméno a roky
  narození volitelně. Bez prohlížeče vrátí jen prvních 20 výsledků, proto hledej co nejúžeji.
  Kartu stáhni `policie_prihlasky.py karta <pořadí> pracovni/karta.jpg Kolar [Jan] [1850] [1870]` (stejné hledání; jde i pořadí
  nad 20) – vypíše citaci a trvalý odkaz (`index.php?action=link&ref=czarch:CZ-100000010:874&karton=K&folium=F`).
- **Nepokrývá Smíchov, Vinohrady, Žižkov, Karlín a další předměstí před 1922** (byla to samostatná města). Náboženství karty neuvádějí.

## Matricula (Rakousko, Bavorsko, Polsko…; data.matricula-online.eu) – `tools/matricula_*.sh`
- Bez přihlášení. Seznam knih: `…/de/oesterreich/<diecéze>/<farnost>/?page=N`; snímek knihy `…/<id>/?pg=<snímek>`
  (zároveň trvalý odkaz).
- URL obrázku obsahuje `csrf` a `ctrl` počítané JavaScriptem → je potřeba prohlížeč (Playwright / Claude in Chrome):
  otevři knihu, klikni na stránku (`.docview-pagelink`), URL obrázku vezmi z `performance.getEntriesByType('resource')`
  a stáhni `bash tools/matricula_dl.sh "<url>" pracovni/x.jpg`. Víc stránek: soubor řádků „<snímek> <url>“ → `matricula_batch.sh`.
- Rejstřík najdeš bez prohlížeče: HTML stránky knihy má seznam `labels` s popisky snímků („04-Index Taufe_0001“).
- Vojenské matriky (např. Štýrský Hradec) tam nejsou – jsou v Kriegsarchivu ve Vídni (offline).

## Polsko – Geneteka (geneteka.genealodzy.pl)
- Zdarma dobrovolnické indexy křtů, sňatků a úmrtí po farnostech; hledej ve webovém rozhraní (vojvodství → farnost →
  příjmení). Index je vodítko – skeny často online nejsou (farní nebo diecézní archiv), pak zápis žádej tam.
- **Farní příslušnost se měnila**: obec mohla patřit k sousední faře (Lipowa → Radziechowy do 1896) – hledej i tam.
- Nestahuj hromadně: PTG uvádí „linkujemy, nie pobieramy danych“ (odkazujeme, nestahujeme) a po desítkách rychlých dotazů
  server vrací nefiltrovaná data. Dotazy dávkuj, s pauzami, a výsledky si ověř.
- Jednotlivý dotaz jde i bez prohlížeče: `https://geneteka.genealodzy.pl/api/getAct.php?draw=1&start=0&length=10&bdm=B&rid=B&w=12sl&search_lastname=<příjmení>&search_name=&search_lastname2=&search_name2=&from_date=1850&to_date=1900&exac=1`
  (`bdm`/`rid` B křty, S sňatky, D úmrtí; `w` vojvodství, např. 12sl slezské, 08op opolské) → JSON. Past: `recordsTotal` > 0
  a prázdné `data` – zkus jen jedno příjmení bez křestního jména a užší roky. Stránkování opakuje řádky.
- Skeny některých polských far jsou i na Matricule (výše) nebo FamilySearch (níže).

## FamilySearch (přes uživatelův přihlášený prohlížeč)
- Přihlášení je potřeba na katalog, snímky i hledání – curl a WebFetch vidí jen přihlašovací stránku. Pracuj jen
  v prohlížeči, kde je uživatel přihlášený a kde to sám nabídne (vestavěný prohlížeč aplikace Claude, Claude in Chrome).
  Neměň mu otevřené karty (po hledání vrať původní adresu). Stránky za Cloudflare neobcházej.
- **Jen běžné prohlížení:** čti stránky a obrázky, které prohlížeč FamilySearch sám načítá. Nevytahuj token ze session
  do vlastních dotazů na interní API (`/platform/…`, `filmdatainfo`) – Claude Code to zablokuje jako obcházení přístupu.
- **Indexy** (české matriky skoro zindexované nejsou, Slovensko ano, hlavně křty): hledání ze stránky lze volat
  `https://www.familysearch.org/service/search/hr/v2/personas?q.surname=…&q.givenName=…&q.fatherGivenName=…&count=20`
  (`fetch(…, {credentials:'include'})`); výsledky v `entries[].content.gedcomx`. Užitečné i na hroby (BillionGraves,
  Find a Grave). Výsledek je vodítko – ověř v matrice.

### Co tam je pro české země (snímky bez indexu)
- **Matriky SOA Litoměřice** – sady „Czech Republic, <okres>, <obec>, <fara>, church records“, v názvu skupiny snímků
  německy („Oschitz, Böhmisch Leipa, Bohemia“). Náhrada, když badatelna SOA Litoměřice nejde. Čísla snímků i stran
  se od badatelny liší (táž kniha: pag. 135 v SOA = pag. 168 na FamilySearch) – v zápisu uveď portál, ze kterého čteš.
- **Sčítání lidu 1869–1910 ze SOA Litoměřice** jsou v katalogu jako **„land records“** („…, <obec>, <ves>, land records,
  1890–1910“, skupiny „… Grundbuchblätter <rok>“) – hledání „census“ najde jen sčítání 1921. Hledej podle místa.
  Na dům připadá pevný počet snímků (1869 a 1910 tři, 1880 a 1900 dva) – snímek domu spočítáš a ověříš na obálce archu.
- **Urbáře panství SOA Zámrsk 1574–1773** (záznamy katalogu `olib:2857880` až `olib:2857980`, „<okres>, <obec>, land
  records“, poznámka „Land registers Urbarios Zamrsk, <č.>, <rok>“) – most přes 17. století. Karta archivu na prvním
  snímku často uvádí folia jednotlivých vsí.
- Sbírka „Czech Republic land records 1750–1889“ (1918632) jsou hlavně pozemkové knihy z Opavska, Litoměřicka a Brněnska.

### Katalog
- Hledání podle místa: `https://www.familysearch.org/search/catalog/results?q.place=Czech Republic, <okres>, <obec>`
  (nebo `+place:"<obec>"`); skupiny předmětů se rozbalují kliknutím.
- **Seznam svazků je stránkovaný po 10** („Page 1 of 2“ pod tabulkou) – přepni na 100 na stránku nebo projdi všechny
  stránky. (Skutečná chyba: oddací knihy fary byly až na druhé stránce a hledání hlásilo, že online nejsou.)
- **Farnost a archiv malé vsi:** wiki „Czechia Town and Parish Finder“ (`https://www.familysearch.org/en/wiki/Czech_Gazetteer_<písmeno>`,
  tabulka obec | německy | farnost | soudní okres | archiv). V prohlížeči stáhni `fetch()` jedno písmeno (~2,7 MB; víc
  najednou nestihne limit nástroje) a filtruj regexem. Tvary jmen se liší (Domaslavice je tam „Domaslovice“).
- **Knihy vedené po vsích:** katalogové roky („Baptisms 1799–1854“) na oddíly malých vsí nesedí – než napíšeš
  „na FamilySearch není“, přečti titulní list a poznámky na konci oddílu (`matriky.md` → „Knihy vedené po vsích“).
  Rejstříky oddaných bývají řazené podle ženicha.

### Čtení snímků bez stahování
- **Seznam snímků skupiny:** `https://www.familysearch.org/search/catalog/film?dgs=<DGS>&i=0` (mřížka; v prohlížeči
  záznamu `view=explore&grid=on`). Miniatury jsou `…/deepzoomcloud/dz/v1/<id>/thumb_p200.jpg`, kde `<id>` je `3:1:<ark>`
  (dřív `apid:TH-…`). Mřížka je virtualizovaná a líná: **pořadí `img` neodpovídá číslu snímku** – číslo ber z předka
  `[aria-label]` („Image N of M“, česky „Snímek“, německy „Aufnahme“) nebo z tlačítka nad miniaturou. Posouvej
  kontejnerem mřížky a id sbírej do `sessionStorage`. Ve skrytém panelu prohlížeče se miniatury nenačtou a snímky
  obrazovky bývají prázdné – ať uživatel panel zobrazí, snímek obrazovky zopakuj.
- **Obrázek snímku:** `https://sg30p0.familysearch.org/service/records/storage/deepzoomcloud/dz/v1/<id>/dist.jpg`
  se načte v `<img>` (`fetch` z jiné adresy ne – CORS); dlaždice 256 px `…/<id>/image_files/<úroveň>/<x>_<y>.jpg`,
  rozměry a nejvyšší úroveň (u každého snímku jiná, 12 nebo 13) v `…/<id>/image.xml`. Na hledání jmen stačí úroveň
  s ~2000 px šířky, na přepis plná.
- **Kontaktní list:** do stránky vlož vlastní vrstvu přes celé okno s mřížkou výřezů z více snímků (`<img>` s
  `max-width:none` posunutý v rámečku s `overflow:hidden`), počkej ~1,5 s na vykreslení a udělej snímek obrazovky.
  Osvědčilo se: pruh jmen (bez číselných sloupců) po polovinách stran, 4 výřezy na snímek obrazovky, víc snímků
  v jedné dávce akcí prohlížeče. Přiblížení (`zoom`) nástroje pro snímek obrazovky rozlišení nepřidá – větší měřítko
  nastav ve vrstvě. Orientačně 11 dvoustran ≈ 1 % pětihodinového limitu.
- Delší skripty pouštěj bez `await` (nástroj pro JavaScript má limit ~45 s) a výsledek ukládej do `window`
  nebo `sessionStorage`. `window.name` přežije přechod mezi `www.familysearch.org` a `sg30p0.familysearch.org` –
  tak předáš seznam id mezi kartami bez vypisování do chatu.
- **Čti sám:** uživatel při ručním procházení přehlédl zápis na sousední dvoustraně.
- **Po ~1000 rychlých požadavcích přijde HTTP 429** a blokace na desítky minut – načítej jen snímky, které čteš,
  nanejvýš pár za sekundu; celé knihy hromadně neprocházej.

### Výřez a citace
- Soubor snímku na disk nástrojem nedostaneš (curl bez přihlášení neprojde, prohlížeč nepošle data na localhost).
  Výřez pro web: ať uživatel snímek uloží do `pracovni/` (stažení v prohlížeči FamilySearch), nebo vezmi snímek
  obrazovky přiblíženého zápisu z výsledku nástroje → `vyrez.py`.
- Citace do zápisu: název sady, **DGS** („číslo skupiny snímků“) a snímek N z M; trvalý odkaz dá
  `https://www.familysearch.org/search/catalog/film?dgs=<DGS>&i=<N−1>` (přesměruje na `ark:/61903/3:1:…`).
  Do `svazky.json` dej DGS, název sady a archiv, ze kterého snímky jsou.

## Hroby a hřbitovy
- Kde jsou předci pohřbeni, víš z rozhovoru s rodinou (Fáze 1). Fotky náhrobků (jména, data, rodná příjmení) jsou
  cenný pramen hlavně pro 20. století, kde matriky ještě nejsou přístupné.
- Evidence hrobových míst: správa hřbitova (kdo je v hrobě uložen, kdo platí nájem – často žijící potomek);
  řada měst má online vyhledávání hrobů. Mezinárodně BillionGraves a Find a Grave.

## Noviny a ročenky – `tools/anno.py`, `tools/anno_snap.py`, `tools/kramerius.py`
**Kdy se vyplatí:** státní a vrchnostenští úředníci, soudci, učitelé, faráři, důstojníci, vojenští lékaři, notáři,
poštmistři, starostové, podnikatelé – noviny otiskovaly jmenování, přeložení, vyznamenání, penze, konkurzy, oznámení
sňatků a parte (zhruba od 1860). Z toho plyne, **kde člověk kdy žil** → kde hledat křty dětí, sňatek, úmrtí.
A když osoba „chybí“ v očekávaných matrikách (stěhovala se se službou). **Spíš ne:** sedláci a řemeslníci na vsi.
- ANNO (rakouské noviny 1700–1950, i Prager Zeitung, Wiener Zeitung): `python3 -I tools/anno.py '"Johann Nowak"' 1860 1915 [stran] [--snip]`
  – jména **německy** („Johann Nowak“, „Wenzel Dworschak“). Výřez místa: `tools/anno_snap.py <docId> "<dotaz>" pracovni/x.jpg`.
  ALEX a annoshow jsou za Cloudflare – neobcházet.
- Kramerius NK ČR (české noviny, ročenky, adresáře): `python3 -I tools/kramerius.py 'text_ocr:"Jan Novák" AND datum_begin:[1900 TO 1910]'`.
  - **Veřejné stránky – celý text:** `https://kramerius5.nkp.cz/search/api/v5.0/item/<uuid stránky>/streams/TEXT_OCR`
    (ztrátové seznamy z 1. světové války v novinách, Chytilův adresář 1914 – fara, pošta, živnostníci v obci).
  - **Chráněné stránky (DNNT/private):** text nejde stáhnout (403), ale hledání funguje: `PID:"<uuid stránky>" AND
    text_ocr:"Příjmení Jméno slovo"~s` vrátí 0/1 – pro s = 0…4 zjistíš, jestli a jak blízko jména je dané slovo (místo,
    útvar), fráze „jméno + nalezené slovo“ pak vrátí v úryvku pár sousedních slov. V seznamech (ročenky, schematismy)
    patří slovo těsně *před* jménem obvykle předchozí osobě. Úryvky jsou u chráněných stránek oříznuté na pár slov.
  - **Regionální Kramerie** mají regionální noviny, místní dějiny a adresáře, které národní Kramerius nemá (seznamy
    vlastníků domů, spolky): Liberecký kraj kvkli.cz (API v5 jako NK, text `/item/<uuid>/streams/TEXT_OCR` u veřejných),
    Královéhradecký svkhk.cz (API v7: `/search/api/client/v7.0/search`, filtr na stránku `fq=pid:"…"`, zvýraznění až
    ~300 znaků kolem slova i u chráněných), další krajské knihovny a MZK. `kramerius.py` zatím umí jen NK.
- Vojenské schematismy: fulltext na archive.org (např. `militrschematis13kriegoog` = 1850).
- **Rizika:** jména se opakují a fulltext šumí („Winter“ = i zima, „Novák“ = nový obyvatel). Ztotožni jen při shodě víc údajů (bydliště,
  funkce navazující na matriku, časová posloupnost). Zdroj je „J“ (jiný pramen) – vodítko a příběh, ne náhrada matriky.
- Výstřižky jsou skvělé na web: ulož do `dokumenty/noviny/`, přes `vyrez.py` a do `dokumenty.json`.
- Pořadí: nejdřív matriky; noviny, když chybí stopa kvůli stěhování, nebo když jde o úředníka/vojáka a chceme příběh.

## Vojáci a legionáři
- **Vojáci z povolání 1918–1950:** sňatky a narození dětí bývají jen ve **vojenských matrikách** (VÚA–VHA Praha, na žádost);
  v civilních a farních knihách místa bydliště pak chybí. Online (vuapraha.cz/vojenske-matriky, kramerius.army.cz) jsou
  jen vojenské matriky zemřelých z 1. světové války.
- **Legionáři – databáze ČsOL** (`csol.cz/legionar/<id>/`): jedna osoba mívá dva záznamy s různým id (jiný den narození);
  druhý bývá úplnější – povolání, **místní jednota ČsOL = kde legionář po válce žil**, fotky (`/wp-content/legionari-obrazky/<id>/…jpg`,
  na legitimaci razítko jednoty). Vyhledávání `?q=` přes stažení stránky nefunguje; sousední id jsou abecedně sousední jména.
  Jednota může rozhodnout mezi dvěma kandidáty stejného jména.

## Ostatní portály – obecný postup
Nástroje pro ně hotové nejsou. Postupuj takto a výsledek zapiš do `STAV.md`, ať to příště víš:
1. Otevři portál v prohlížeči (Claude in Chrome / Playwright, pokud jsou k dispozici; jinak požádej uživatele).
   Najdi fond „Sbírka matrik“ / „Matriky“ a svazek podle obce a let.
2. **Snímek:** většina prohlížečů má tlačítko ke stažení obrázku – ulož do `pracovni/`. Když ne, podívej se v síťovém
   provozu, odkud se načítají dlaždice/obrázky (IIIF, DeepZoom, Zoomify), a stáhni celý obrázek touto cestou – jednotlivě,
   jen snímky, které čteš. Krajní možnost: požádej uživatele, ať snímek uloží a dá do `pracovni/`.
3. **Trvalý odkaz** na snímek (tlačítko „trvalý odkaz“/permalink, jinak URL svazku + číslo snímku) dej do `odkaz` v zápisu.
4. Svazek zapiš do `data/svazky.json` ručně: `"klic": {"archiv": "SOA Třeboň", "portal": "digi.ceskearchivy.cz",
   "svazek": "N Volary 1784–1820, sign. …", "popis": "obce…", "url": "<odkaz na svazek>"}`.
5. Dál stejně jako u ARON: `vyrez.py`, `ramecek.py`, přepis, osoby, deník.
6. Když se postup osvědčí, napiš pro portál vlastní malý nástroj podle `trebon.py` (bez prohlížeče, pokud to jde)
   a postup zapiš do `STAV.md`. Poznatek zapiš i do `poznamky_pro_skill.md` (pro správce skillu).

## Starší prameny (17.–18. století)
- **Soupis poddaných podle víry 1651** – celé rodiny s věkem, po krajích; edice Národního archivu jako PDF
  (nacr.cz, hledej „Soupis poddaných podle víry“ + kraj). Fulltext v PDF, příjmení často bez diakritiky / s jinou ortografií
  (Šaršoun → „Šaroun“, dlouhé ſ jako f). Ves je v rámci panství; poznamenej si stránku edice.
- **Berní rula 1654** – jen hospodáři s půdou; edice a rejstříky v knihovnách (Kramerius/DNNT).
- **Gruntovní (pozemkové) knihy** – převody domů z otce na syna; online jen část (SOA Plzeň téměř vše, SOA Praha část,
  ostatní spíš badatelna). Fond „Velkostatek <panství>“.
- **Mapy stabilního katastru (1824–43)** – kde stál dům s číslem popisným: Archiv ČÚZK na **ags.cuzk.gov.cz/archiv/**
  (stará adresa archivnimapy.cuzk.cz vrací 404). Najdi katastrální území, klikni do mapy a vyber druh mapy (indikační
  skica, originální mapa stabilního katastru, katastrální mapa); list se otevře v prohlížeči map.
  **Past:** černá čísla v budovách na katastrálních mapách jsou **čísla stavebních parcel, ne čísla popisná**. Čísla
  stavebních parcel se drží často dodnes – přes RÚIAN (adresní místo „Obec čp.“ → stavební objekt → parcela) najdeš
  dům i na pozdější a dnešní mapě; dům ale mohl být zbořen a postaven se stejným čp. jinde.
  Na **císařských otiscích** chybí u části listů barvy a čísla domů. Lepší jsou **indikační skici**: mají čísla domů (červeně)
  a u pozemků jméno majitele („N. 13“ = patří k domu čp. 13). Dům bez pozemků mimo ves = domkář bez polí.
  Jméno majitele samotného domu bývá jen v písemném operátu (archiv, ne online). Výřezy map patří na web k rodině.
- **Dnešní adresa domu** podle čísla popisného: RÚIAN (ČÚZK, vrstva AdresniMisto). Pozor, staré centrum mívá od 19. století
  stejná čp., ale předměstí a vesnice čísla přečíslovávaly. Hodí se na „procházku po stopách předků“.
  Stavbu podle obce a čísla popisného najde i nahlizenidokn.cuzk.gov.cz (ověření adresy z dokladu); vlastník je za
  CAPTCHou a je to údaj o žijícím člověku – nezjišťuj ho.

## Oběti 2. světové války
- **Arolsen Archives** (collections.arolsen-archives.org): dokumenty o vězních, nuceně nasazených a vysídlených. Vyhledávání
  v prohlížeči, vstupní prohlášení musí odsouhlasit uživatel.
- **Mauthausen – Raum der Namen** (raumdernamen.mauthausen-memorial.org): vězni zemřelí v Mauthausenu, s datem a místem
  narození i úmrtí. Takové údaje jsou citlivé – na web jen se souhlasem rodiny (`soukromi.md`).

## Příjmení dnes a DNA
- **Rozšíření příjmení dnes**: kdejsme.cz (počty nositelů po okresech). Rychle ukáže, jestli je příjmení vzácné a kde
  jsou jeho „hnízda“. Při hledání vzdálených příbuzných vyškrtni vlastní rodinu.
- **DNA** (jen když o to uživatel stojí, a jeho rozhodnutí): autosomální test (MyHeritage, Ancestry) najde bratrance
  do ~5. kolene. **Y-DNA** (FamilyTreeDNA, Y-37 až Big Y) se dědí po meči beze změny. Ověří, jestli dvě linie stejného
  příjmení mají společného předka, a u nemanželského dítěte může shoda s jiným příjmením ukázat otce. Kontakt se žijícími
  příbuznými vždy jen přes uživatele.
Všechno, co jde jen v badatelně, zapisuj do `data/archivni_dotazy.md` (archiv, fond, inventární číslo, co hledat).
