# Soukromí, etika a cizí služby

## Žijící lidé
- Na webu jen jméno a rok narození (`"note": "Žijící – údaje jen základní."`). Žádné adresy, telefony, rodná čísla,
  zdravotní údaje, rozvody, nemanželské děti u žijících či nedávno zemřelých bez souhlasu rodiny.
- Platí i pro boční příbuzné (sourozence předků z 20. století). `kontrola.py` hlásí `ŽIJÍCÍ?` u každého, kdo se narodil
  před méně než 100 lety, nemá zapsané úmrtí a v jeho textu nebo faktech je přesné datum či číslo domu. Zeptej se
  uživatele: zemřel-li, doplň † (do `y` nebo faktů); žije-li, nech jen jméno a rok narození.
- Citlivé věci z nedávné minulosti (sebevraždy, věznění, nemoci) – zeptej se uživatele, jestli a jak je zmínit.
- Matriční údaje starší než lhůty jsou veřejné, ale ohleduplnost platí i pro ně (zbytečně nezesměšňovat).

## Před zveřejněním webu (i před odesláním souboru z `jeden_soubor.py`) projdi s uživatelem
`python3 -I tools/kontrola.py` hlásí `CITLIVÉ` u textů z posledních ~100 let (sebevražda, nemoc, rozvod, dluhy, nemanželské
dítě…), které jdou na web – v poznámkách osob, ve „Co hledáme“ (`ISSUES`), u bočních příbuzných, v zajímavostech a v příběhu.
Údaje z rodinného stromu (GEDCOM) a od rodiny bývají právě takové – pro výzkum ano, na web jen se souhlasem.
U osob a bočních příbuzných rozhoduje rok narození (od 1870 dál), ne libovolný rok v textu – nemanželské dítě z 19. století
se nehlásí, i když poznámka zmíní sčítání 1921. Co uživatel výslovně schválí, zapiš do `data/web.json` → `citlive_schvaleno`,
jedním ze dvou tvarů:
- místo a slovo `"osoba 26: nemanželsk"` (přesný řetězec napíše hláška; `"*: dluh"` platí všude, jen název místa platí
  pro všechna slova v něm),
- úryvek textu s hlášeným slovem `"oběsil se ve stodole"` – platí jen pro to místo v textu; když se text změní, hlásí se znovu.

Tento seznam na web nejde.
1. Seznam žijících osob na webu a co o nich web říká.
2. Rodinné fotky a dokumenty – souhlasí ti, kdo jsou na nich (nebo jejich rodina)?
3. Přihlašovací otázka a odpověď (`web.json`) – nastavená a dost těžká?
4. Kontakt na webu – chce tam uživatel svůj e-mail?
Teprve pak `npm run nasadit`.

## Placené a cizí služby (MyHeritage, Ancestry, Geni, FamilySearch)
- Přihlášení, platby a předplatné řeší **jen uživatel**. Zkušební verze se po skončení automaticky platí – připomeň,
  kdy končí a kde ji zrušit.
- **Žádné hromadné procházení ani stahování.** Skutečná zkušenost: automatické stažení ~180 záznamů z MyHeritage vedlo
  k zablokování účtu „kvůli možnému zneužití“ – uprostřed placené zkušební doby. Čti jen jednotlivé záznamy,
  které jsou potřeba, tempem člověka; raději požádej uživatele o export (GEDCOM) nebo o konkrétní stránky.
- Údaje odtud jsou stav `mh` a vždy se ověřují v matrikách.

## Archivní portály
Jsou zdarma a veřejné, ale servery mají omezené síly: stahuj jen snímky, které opravdu čteš, žádné celé svazky naráz,
paralelně maximálně pár požadavků. Citace vždy až na úroveň snímku (aby to šlo zkontrolovat).

## Rodokmen v jednom souboru
Soubor z `jeden_soubor.py` nemá přihlášení: kdo ho dostane (a komu ho přepošle), vidí všechno včetně poznámek a zápisů.
Proto stejný postup jako před zveřejněním webu a výslovný souhlas uživatele; upozornění `ŽIJÍCÍ?` a `CITLIVÉ` nástroj vypíše.

## Data v gitu a sdílení
Projekt obsahuje osobní údaje rodiny. Když ho uživatel chce mít na GitHubu, pak **jen jako soukromé (private) repo**.
