# Rodinný web – stavba, nastavení, zveřejnění

Web je statický (Astro + vyhledávání Pagefind), data bere z `data/` přes `tools/export_web.py`.
Stránky: úvod (lákadlo, statistiky, zajímavosti, mapa, rody, vějíř), příběh, zajímavosti, rody, stránka rodu,
mapa (OpenStreetMap), vějíř přes celou obrazovku s hledáním, seznam předků, zápisy (s výřezem, rámečkem, přepisem
a překladem), stránka osoby, rodiny, „Co hledáme“, výzkumný deník, hledání.

## Příkazy (ve složce `web/`)
| příkaz | co dělá |
|---|---|
| `npm install` | jednou na začátku (stáhne knihovny, ~1 minuta) |
| `npm run data` | převede data do webu (vždy po změně dat; funkční Python 3 vyhledá `scripts/data.mjs`) |
| `npm run build` | sestaví web do `dist/` |
| `npm run nahled` | data + build + náhled na http://localhost:4321 (Ctrl+C ukončí) |
| `npm run dev` | vývojový režim při úpravách vzhledu |
| `npm run nasadit` | data + build + nahrání na Netlify |

Náhled spouštěj na pozadí a uživateli pošli odkaz. Vzhled si ověř sám (snímek obrazovky přes prohlížeč, je-li k dispozici).

## `data/web.json`
```json
{
 "nazev": "Rodokmen Novákových",
 "popis": "Popis pro vyhledávače a sdílení (web je ale noindex).",
 "zapati": "Dohledáno v digitalizovaných matrikách SOA Zámrsk (portál ARON)",
 "kontakt": {"jmeno": "Petrovi", "email": "petr@example.cz"},
 "prihlaseni": {"uvod": "Tenhle web je jen pro rodinu.", "otazka": "Jak se jmenoval pes u babičky v Holicích?", "odpoved": "Alík"},
 "uvod": {"nadpis": "Lákavý nadpis", "odstavce": ["2–3 věty, které chytí"], "foto": "klic_obrazku_ve_vyrezech", "foto_popis": "…"},
 "pribeh": {"menu": "Příběh Nováků", "rod": 8, "tlacitko": "Přečíst příběh Nováků"},
 "zajimavosti_na_uvodu": [{"nadpis": "Nejstarší předek", "text": "Kovář Jan, asi 1825."}],
 "citlive_schvaleno": ["osoba 26: nemanželsk"]
}
```
- `kontakt.jmeno` je ve 3. pádě („Napište Petrovi na …“).
- **Přihlášení:** otázka, na kterou zná odpověď jen rodina (ne snadno dohledatelná na sociálních sítích).
  Odpověď se porovnává bez diakritiky a velkých písmen. Na serveru i v cookie prohlížeče je jen její otisk (SHA-256),
  samotná odpověď se nikam neukládá. Krátkou nebo běžnou odpověď (jméno, obec) ale jde z otisku uhádnout zkoušením,
  proto ať ji uživatel nepoužívá jako heslo jinde. Bez odpovědi nasazení (`npm run nasadit`, `kontejner`, `deploy-caprover`)
  skončí chybou; otevřený web jen výslovně přes `"otevreny": true` v `prihlaseni`.
  Je to lehká ochrana proti náhodným návštěvníkům, ne bankovní zabezpečení – citlivé věci na web nepatří.
- `citlive_schvaleno` = citlivé údaje, které uživatel schválil ke zveřejnění (`kontrola.py` je pak nehlásí; na web nejde):
  místo a slovo (`"osoba 26: nemanželsk"`, `"*: dluh"`) nebo úryvek textu s hlášeným slovem (`"oběsil se ve stodole"`;
  když se text změní, hlásí se znovu), viz `soukromi.md`.
- `uvod.foto` = klíč obrázku ve `vyrezy/` (ulož přes `vyrez.py`).
- `pribeh`: `menu` a `tlacitko` pojmenuj podle hlavního rodu („Příběh Novákových“), `rod` = číslo rodu (8–15).
  Bez vyplněného `uvod` ukáže úvodní stránka aspoň název a `lead` příběhu. Viz `pribehy.md`.
- Šablona `web.json` je prázdná – název nastav hned, jak znáš příjmení výchozí osoby (`kontrola.py` hlásí zbytky ukázky).
- `puvodni_jmena`: `true` = jména osob na webu a ve vějíři v původních tvarech ze zápisů (pole `zap` v `osoby.json`,
  „Catharina Nowakin / Kateřina Nováková“). Výchozí je dnešní spisovná podoba; původní tvar je pak jen řádkem na stránce osoby.

## Stránky Statistiky a Domy
- **Statistiky** (`/statistiky/`, `tools/statistiky.py`): povolání, věk dožití (muži a ženy, podle století narození),
  věk při sňatku (rozložení, podle století, věkový rozdíl manželů), vzdálenost rodišť manželů (souřadnice z `mista.json`),
  měsíce svateb, počet dětí v rodině, dětská úmrtnost a pořadí předka mezi sourozenci, povolání i podle století,
  generační odstup, místa narození, křestní jména předků i sourozenců (celkem, podíly podle století, jméno po zemřelém
  sourozenci), víra, zápisy podle druhu a archivu. Počítá se z faktů přímých předků –
  čím jednotnější zápis faktů (`* 12. 3. 1873 Obec čp. 5`, `× …`, `† …` s věkem ze zápisu, řemeslo samostatně), tím lepší
  čísla. Děti v rodině a dětská úmrtnost jen z rodin, kde má předek `"sour": "hotovo"`: děti = předek a jeho sourozenci
  `bratr`/`sestra`; dětství přežil, kdo má sňatek, povolání nebo údaj aspoň 15 let po narození, jinak „nevíme“.
- **Domy** (`/domy/`, `tools/domy_export.py`): mapa domů předků z výstupu skillu stare-adresy (viz `data.md` → `domy/`).
  Podklad ČÚZK (mapa / letecký snímek), domy shluknuté podle obcí, barva podle rodu, v okénku lidé, kteří v domě
  žili (přímí předci první, boční příbuzní s odkazem na kartičku u předka), výřez skici a jedna věta o jistotě polohy.
  Na stránkách osob a zápisů jsou odkazy na domy. Výřezy skic na veřejném webu jen s citací archivu (podmínky
  v návodu stare-adresy).

## Zveřejnění na Netlify (výchozí, zdarma)
1. Uživatel si založí účet na netlify.com (stačí přihlášení přes Google/GitHub) – udělá sám.
2. Přihlášení CLI (otevře prohlížeč) – dej uživateli: `! cd web && npx -y netlify-cli@latest login`.
   Když `!` nejde (cloudové prostředí): `npx -y netlify-cli@latest login --request "Rodokmen"` vypíše odkaz a číslo
   lístku – uživatel odkaz otevře a schválí, pak `npx -y netlify-cli@latest login --check <lístek>`.
3. Založení webu a propojení složky (interaktivní, jednou) – dej uživateli:
   `! cd web && npx -y netlify-cli@latest sites:create` (zvolí tým a název → adresa `https://<název>.netlify.app`),
   případně `npx netlify-cli link`, pokud web už existuje. Je-li uživatel už přihlášený, jde web založit i bez dotazů
   (můžeš spustit sám): `cd web && npx -y netlify-cli@latest sites:create --name <název> --account-slug <tým>`.
   **Windows:** když `!` běží ve Windows PowerShellu 5.1 (`&&` tam nefunguje a `npx` blokuje Execution Policy), ať uživatel
   otevře PowerShell 7 nebo Příkazový řádek, přejde do složky `web` a spustí `npx -y netlify-cli@latest login` (a `sites:create`).
4. Nasazení: `cd web && npm run nasadit` (můžeš spustit sám; vypíše adresu webu).
5. Ověř: otevři adresu **v anonymním okně** → musí se ukázat rodinná přihlašovací otázka; po správné odpovědi web.
   Ukáže-li se místo ní přihlášení k Netlify (401, „Login Redirect“), zdědil web ochranu týmu („Team protection“).
   Uživatel ji vypne v administraci webu: Project configuration → Access & security → Visitor access. Web pak chrání
   rodinná otázka – proto znovu ověř v anonymním okně, že se ukáže.
   Přihlášení zajišťuje Netlify Edge Function `web/netlify/edge-functions/brana.js` (generuje ji export).
Další aktualizace = jen `npm run nasadit`. Tarif zdarma má měsíční kredity a každé nasazení je spotřebovává –
nenasazuj po každé drobné změně, ale až na požádání uživatele (třeba po skončení kola hledání). Vlastní doménu lze nastavit v administraci Netlify.

**Pozor:** „Netlify Drop“ (přetažení složky v prohlížeči) neumí Edge Functions → web by byl bez přihlášení. Nepoužívat.

## Náhled v Claude desktop
Projekt má `.claude/launch.json` – náhled webu v Claude desktop spustí `npm --prefix web run dev` (port 4321). Data se
předtím musí vyexportovat (`cd web && npm run data`). Když náhled nenaběhne (třeba na Windows, kde je `npm` jako `npm.cmd`),
zkus v `launch.json` `"runtimeExecutable": "node"` a `"runtimeArgs": ["web/node_modules/astro/bin/astro.mjs", "dev", "--root", "web"]`
(Astro 7 má spouštěč `astro.mjs`, ne `astro.js`). Server běží jen na tomto počítači – nepřidávej `--host`.

## Vlastní server (pokročilé)
- Podman: `cd web && npm run kontejner` – zkontroluje přihlašovací odpověď, převede data a sestaví image `rodokmen-web`
  podle `web/Dockerfile` (build Astro → nginx s `nginx.conf` z `nginx.sablona.conf`). Vyzkoušení:
  `podman run --rm -p 8080:80 rodokmen-web` → http://localhost:8080. Image pak nahraj na server (`podman save` / registr).
  Nestavěj image holým `podman build` – bez `npm run data -- --nasazeni` by mohl vzniknout web bez přihlášení.
  Na macOS a Windows potřebuje Podman běžící virtuální stroj (`podman machine init`, `podman machine start` – dej uživateli).
- CapRover: `npm run deploy-caprover` (vyžaduje nainstalovaný a přihlášený `caprover` CLI).

## Úpravy vzhledu
Styly `web/src/styles/global.css` (barvy v `:root`), rozložení `web/src/layouts/Base.astro`, stránky `web/src/pages/`.
Barvy rodů jsou v `tools/export_web.py` (`LINE_COLORS`) a `tools/fan_chart.py` (`BASE`). Upravuj jen na přání uživatele
a po úpravě zkontroluj web na mobilu i počítači.

## Vějíř jako plakát
`python3 -I tools/fan_chart.py vystupy/` → SVG a HTML (a PNG, je-li nainstalovaný Google Chrome, na Windows i Microsoft Edge) k tisku.

## Rodokmen v jednom souboru (ke sdílení bez webu)
`python3 -I tools/jeden_soubor.py` vytvoří ve `vystupy/` dva soubory HTML se vším, co je na webu (stejná data jako
`npm run data`), včetně zmenšených výřezů zápisů – bez serveru, bez internetu, pošle se e-mailem, na flashce, přes WhatsApp:
| soubor | pro koho |
|---|---|
| `rodokmen.html` | počítač a prohlížeč v telefonu: navíc hledání, přibližování vějíře, stromový graf, filtr zápisů; bez JavaScriptu funguje taky |
| `rodokmen-bez-js.html` | náhled přílohy v telefonu (iPhone Mail/Soubory/WhatsApp, Android) a pošta, která soubory se skripty blokuje |
- Velikost hlavně podle obrázků (142 výřezů ≈ 13 MB): menší `--sirka 800 --kvalita 40`, úplně bez `--bez-obrazku`;
  dlouhý deník vynechá `--bez-deniku`; jen jeden soubor `--jen-js` / `--jen-bez-js`. Potřebuje ImageMagick.
- **Soubor nemá přihlášení** – kdo ho dostane, vidí všechno. Před vytvořením nástroj vypíše upozornění `ŽIJÍCÍ?`
  a `CITLIVÉ` z `kontrola.py`; vyřeš je s uživatelem a soubor dávej jen s jeho souhlasem (`reference/soukromi.md`).
- Mapa bez internetu je jen přibližný obrys Česka s obcemi (výřez podle obcí); přesná mapa s podkladem je na webu.
- Bez JavaScriptu se panely otvírají přes `#kotvy`: Zpět v prohlížeči panel zavře, Zavřít skočí na začátek stránky.

## Aktualizace staršího projektu
Znovu spusť `python3 -I SKILL_DIR/tools/novy_projekt.py <složka projektu>`. Data (`data/`, výřezy) zůstanou, `tools/` se přepíše
a soubory ve `web/`, které se liší od nové šablony, taky – staré verze uloží do `pracovni/zaloha_web_<datum>/` a vypíše jejich seznam.
Upravoval-li jsi s uživatelem vzhled (styly, stránky), převezmi úpravy ze zálohy (porovnej soubory) a ověř web.
Nástroje upravené v projektu (třeba `export_web.py`) uloží aktualizace před přepsáním do `pracovni/zaloha_nastroje_<datum>/`
a vypíše je – úpravu přenes do nové verze (nová verze mohla stejné místo změnit jinak, tak je slaď, ne jen zkopíruj starý
soubor) a navrhni ji i do `poznamky_pro_skill.md`, ať ji dostanou všichni. Vlastní skripty projektu, které skill nemá, zůstanou. Pak ve `web/`
`npm install` a `npm run data`. Starou šablonu přihlášení `export_web.py` odmítne s výzvou k aktualizaci.
