# Pachetul „Financiara" — industria financiară din România

20 de seturi de date pregătite pentru integrare pe 24reco.com, generate la 18 septembrie 2026.
Pentru fiecare set: un fișier Excel, o pagină HTML de sine stătătoare și un script Python de
re-descărcare. Plus `Financiara 00 index.html`, pagina-index a pachetului.

**17 din 20 de seturi sunt lunare.** Cele 3 trimestriale (`03 02`, `03 03`, `04 04`) sunt marcate
ca atare în foaia `Sursa`, în badge-ul paginii, în footer și în prima notă metodologică — pentru
ele nu există echivalent lunar, din motivele explicate mai jos.

---

## 1. Ce conține fiecare set

**Excel** (`Financiara NN MM.xlsx`)

| Foaie | Conținut |
|---|---|
| `Sursa` | Sursa, URL, codul exact al setului / cheia SDMX, frecvența, perioada, unitatea de măsură, data descărcării, licența, metodologia, notele și capcanele cunoscute. |
| `Date` | Datele brute, în format lung, exact cum au fost descărcate. Nicio agregare, nicio corecție. |
| 6–9 foi de analiză | Valori calculate cu pandas (nu formule Excel): variații lunare și anuale, medii mobile, structuri procentuale, comparații regionale, clasamente, minime și maxime istorice. |

**Pagina HTML** (`Financiara NN MM.html`) — un singur fișier, cu datele înglobate direct în pagină
(zero apeluri de rețea pentru date). 4 indicatori de titlu, 4–5 grafice Chart.js, tabel cu ultimele
36 de perioade și note metodologice cu sursa. Temă deschisă și întunecată, fără derapaj orizontal
la 390 px. Singura resursă externă este biblioteca Chart.js, încărcată de la
`cdn.jsdelivr.net/npm/chart.js@4.4.3`.

**Scriptul** (`scripts/financiara_NN_MM.py`) — re-descarcă datele și regenerează ambele fișiere.
Toate scripturile folosesc `fin_common.py` și se opresc cu eroare, **fără să suprascrie datele
bune**, dacă sursa întoarce prea puțin, gol sau date mai vechi decât toleranța setului.

```bash
pip install pandas openpyxl requests
python3 scripts/financiara_02_01.py      # regenerează un set
python3 scripts/build_index.py           # regenerează pagina-index
python3 check_html.py 'out/*.html'       # verifică paginile (necesită playwright)
```

---

## 2. Cele 20 de seturi

### 01 Piața de capital

| Cod | Titlu | Sursă | Frecv. | Perioadă |
|---|---|---|---|---|
| 01 01 | Randamentul titlurilor de stat pe 10 ani (Maastricht) | Eurostat `irt_lt_mcby_m` | lunară | 2005-04 → 2026-08 |
| 01 02 | Activitatea de tranzacționare și capitalizarea BVB | BVB, buletine lunare (PDF), secț. A | lunară | 2010-01 → 2026-08 |
| 01 03 | Indicii Bursei de Valori București | BVB, buletine lunare (PDF), secț. A | lunară | 2010-01 → 2026-08 |
| 01 04 | Ratele dobânzii de pe piața monetară (ROBOR) | Eurostat `irt_st_m` | lunară | 2007-01 → 2026-08 |
| 01 05 | Structura pe sectoare a BVB | BVB, buletine lunare (PDF), secț. D.1 | lunară | 2010-01 → 2026-08 |

### 02 Bănci

| Cod | Titlu | Sursă | Frecv. | Perioadă |
|---|---|---|---|---|
| 02 01 | Dobânzile la creditele noi | BCE, ECB Data Portal, `MIR` | lunară | 2007-01 → 2026-07 |
| 02 02 | Dobânzile la depozite și marja bancară | BCE, `MIR` | lunară | 2007-01 → 2026-07 |
| 02 03 | Creditele și depozitele din bilanțul băncilor | BCE, `BSI` | lunară | 2007-01 → 2026-07 |
| 02 04 | Cursul de schimb al leului și dobânzile de referință | BCE `EXR` + BIS `WS_CBPOL` + Eurostat `irt_st_m` | lunară | 2007-01 → 2026-08 |

### 03 Asigurări

| Cod | Titlu | Sursă | Frecv. | Perioadă |
|---|---|---|---|---|
| 03 01 | Prețul asigurărilor în inflație (IAPC) | Eurostat `prc_hicp_minr` + `prc_hicp_iw` | lunară | 2005-01 → 2026-08 |
| 03 02 | Piața asigurărilor: prime, daune, cheltuieli | EIOPA, `SQ_Premiums_Claims_Expenses.csv` | **trimestrială** | 2016-Q3 → 2026-Q1 |
| 03 03 | Cât de solizi sunt asigurătorii din România | EIOPA, `SQ_Own_Funds.csv` + `SQ_Balance_Sheet.csv` | **trimestrială** | 2016-Q3 → 2026-Q1 |

### 04 Investiții financiare

| Cod | Titlu | Sursă | Frecv. | Perioadă |
|---|---|---|---|---|
| 04 01 | Fluxurile de investiții financiare cu restul lumii | Eurostat `bop_c6_m` | lunară | 2007-01 → 2026-06 |
| 04 02 | Unde își țin banii românii: depozitele pe maturități și sectoare | BCE, `BSI` | lunară | 2007-01 → 2026-07 |
| 04 03 | Fondurile de investiții din România | BCE, `IVF` | lunară | 2008-12 → 2026-07 |
| 04 04 | Activele financiare ale gospodăriilor | Eurostat `nasq_10_f_bs` | **trimestrială** | 2007-Q1 → 2026-Q1 |

### 05 Pensii private

| Cod | Titlu | Sursă | Frecv. | Perioadă |
|---|---|---|---|---|
| 05 01 | Pilonul II: participanți, active nete și contribuții | ASF, `p2-date_statistice.xlsx` | lunară | 2008-05 → 2026-07 |
| 05 02 | Pilonul II: unde sunt investiți banii | ASF, `p2`, Table 6 | lunară | 2008-06 → 2026-07 |
| 05 03 | Pilonul II: VUAN și randamentele fondurilor | ASF, `p2`, Table 5 + 15 | lunară | 2008-05 → 2026-07 |
| 05 04 | Pilonul III: pensiile facultative | ASF, `p3` + `p2` pentru comparație | lunară | 2007-09 → 2026-07 |

Surse distincte: Eurostat (5), Banca Centrală Europeană (6), ASF (4), BVB (3), EIOPA (2),
plus BIS ca sursă secundară în `02 04`.

---

## 3. Capcane confirmate live (18 septembrie 2026)

### Surse care NU funcționează din mediul de execuție
- **bnr.ro** — WAF F5, răspuns de 730 B pentru orice cale, inclusiv fișierele XML de curs valutar
  și `robots.txt`. Ocolit integral prin BCE și BIS, care republică datele raportate de BNR.
- **insse.ro / TEMPO portul 8077** — inaccesibil.
- **data.gov.ro** — conexiunea TLS eșuează constant prin proxy (HTTP 000).
- **aaf.ro** (Asociația Administratorilor de Fonduri) — HTTP 500, bază de date stricată. Acoperit
  prin setul BCE `IVF` (`04 03`).
- **fgdb.ro** (Fondul de garantare a depozitelor) — Cloudflare 403.
- **paginile de navigare asfromania.ro** — WAF TSPD (răspuns „Request Rejected", 245 B). Fișierele
  statice de pe `data.asfromania.ro` NU sunt afectate.
- **cdnjs.cloudflare.com** — blocat; de aceea paginile folosesc jsdelivr.

### ECB Data Portal
- Ruta veche (`/service/data/...` prin gazda anterioară) era moartă în pachetele precedente;
  **`https://data-api.ecb.europa.eu/service/data/{FLOW}/{KEY}?format=csvdata` funcționează**.
- **Numărul de puncte din cheie trebuie să fie exact numărul de dimensiuni al setului**, altfel
  primești HTTP 400 cu o pagină HTML, nu un mesaj de eroare. MIR = 10, BSI = 11, IVF = 10, EXR = 4,
  SEC = 9. Descoperirea cheilor: `?detail=serieskeysonly&format=csvdata` pe o cheie complet wildcard.
- `&detail=dataonly` reduce răspunsul de aproximativ 9×.
- **Cheie existentă ≠ date.** Serii apar în `serieskeysonly` și au zero observații (ex. `L23.D`,
  `L23.E` pentru RO).
- MIR pentru România este practic **numai în lei**; singura serie în euro e DAE la creditele de
  locuință. Seriile „totale" MIR încep abia în 2017-08 — pentru istoric din 2007 se folosesc
  perioadele de fixare a dobânzii.
- **BSI raportează în euro**, convertit la cursul de final de lună, deci variațiile în euro conțin
  efect de curs; ritmurile corecte sunt seriile oficiale `DATA_TYPE=I`, `BS_SUFFIX=A`.
- Sectorul total se scrie `0000` în cheie, deși CSV-ul îl afișează ca `0`.
- **IVF acoperă România** (911 serii lunare din 2008-12), contrar unui prim test care dădea 404 —
  cauza era `BS_COUNT_SECTOR` scris `0` în loc de `0000`.
- **SEC nu e utilizabil pentru RO**: 359 de serii, dar toate se opresc în 2021-12.
- `CBD2`, `ICB`, `ICO`, `LIG` (bănci consolidate, asigurări) **nu acoperă România**.

### Eurostat
- **`prc_hicp_midx`, `prc_hicp_manr` și `prc_hicp_inw` sunt înghețate la 2025-12** (ECOICOP ver. 1).
  Setul viu este **`prc_hicp_minr`** (ECOICOP ver. 2), cu date până în 2026-08.
- În `prc_hicp_minr` dimensiunea se numește **`coicop18`**, nu `coicop`, iar totalul este `TOTAL`;
  `CP00` dă HTTP 400. În seturile vechi era exact invers.
- Renumerotare ECOICOP v1 → v2: CP125 → **CP121**, CP1252 → CP1213, CP1254 → **CP1214**, plus noua
  subclasă **CP12141** (asigurarea autoturismului). România raportează CP121, CP1213, CP1214,
  CP12141; NU raportează asigurările de viață și de sănătate separat.
- **`bop_c6_m`**: cererea nefiltrată întoarce HTTP 413 (`EXTRACTION_TOO_BIG`, peste 16 milioane de
  rânduri estimate) sau `ASYNCHRONOUS_RESPONSE`. Necesită filtrare simultană pe 7 dimensiuni.
  Codurile folosesc **dublu underscore** (`FA__P__F3`); un cod greșit întoarce HTTP 200 cu `value`
  gol, nu eroare. **Activele de rezervă (`FA__R__F`) nu au date pentru România.**
- Eurostat listează uneori eticheta lunii curente fără valori — filtrarea se face după valoare, nu
  după etichetă.

### DG ECFIN (ancheta de conjunctură)
- Eticheta directorului este **YYMM** (`nace2_ecfin_2608`), nu YYYYMM, iar fișierul se numește
  **`services_subsectors_nsa_nace2.zip`**, fără `_m_` (acela e numele XLSX-ului din interiorul
  arhivei). O cale inexistentă întoarce **HTTP 200 cu pagina de aterizare HTML** după un redirect
  301 — de aici obligativitatea verificării semnăturii `PK`.
- **Blocajul de fond:** România **nu mai raportează CAEN 64 din ianuarie 2009** și **nu a raportat
  niciodată CAEN 65 sau 66**. Din acest motiv pachetul nu conține niciun set de încredere a
  sectorului financiar — ar fi fost o pagină fără niciun număr românesc.

### BVB
- `robots.txt` întoarce HTTP 404 — deci fără restricții, conform RFC 9309.
- Buletinele lunare au tipar de URL 100% fiabil:
  `https://bvb.ro/info/Rapoarte/Lunare/{LUNA_ROMÂNEȘTE_MAJUSCULE}{AN}.pdf`, verificat pe toate
  cele 200 de luni din 2010-01 până în 2026-08.
- Structura secțiunii A are **trei formate** (2010–2013, 2014–2019, 2020–prezent); în formatele noi
  eticheta stă *între* linia RON și linia EUR, iar o parsare naivă inversează numărul de titluri cu
  numărul de tranzacții.
- Validare independentă: variațiile lună/lună calculate din valorile extrase coincid la a doua
  zecimală cu cele raportate de BVB în buletin.
- Golurile din serii sunt reale, nu erori de parsare: BET-BK și BETPlus încep în 2014-06, BET-TR în
  2014-09, BET-C a fost retras în 2014-05, ROTX e raportat în lei doar până în 2012-07.

### ASF
- **`https://data.asfromania.ro/pensii/p2-date_statistice.xlsx`** și **`p3-date_statistice.xlsx`**
  sunt singurele fișiere ASF descărcabile programatic găsite. Nu există echivalent pentru asigurări
  sau piață de capital (testate peste 15 variante de cale, toate 404).
- **Capcană gravă: o cale inexistentă întoarce HTTP 200 cu 0 octeți.** Un downloader care verifică
  doar codul de status scrie un fișier gol peste datele bune.
- Fișierele sunt actualizate **in-place**: istoricul stă în coloane, nu într-un fișier pe lună.
- Tabelele sunt **stivuite vertical în aceeași foaie**, coloana antetului variază între B și C,
  rândul `TOTAL` nu are număr de ordine, iar denumirile fondurilor apar când cu majuscule, când
  normal (`VITAL` / `Vital`).
- **Rata de rentabilitate e stocată ca fracție** (0,107 = 10,7%) și e anualizată pe 60 de luni din
  2020 încoace, pe 24 înainte — verificat empiric prin reproducerea CAGR-ului VUAN.
- ASF publică rapoarte rectificative care **modifică retroactiv valori deja publicate**.

### EIOPA
- Fișierele nu sunt pe eiopa.europa.eu, ci pe
  `nexteuropa-multisites.s3.eu-west-1.amazonaws.com/www.eiopa.europa.eu/assets/insurance-statistics/`.
- Valorile din S.05.01 sunt **cumulate de la începutul anului** (T1 < T2 < T3 < T4, reset în ianuarie).
  Fără de-cumulare, comparațiile între trimestre sunt greșite.
- `SQ_Balance_Sheet.csv` **nu e UTF-8** — se citește cu `latin-1`.
- Sumele absolute de fonduri proprii nu există pe linia „All undertaking types"; se însumează
  tipurile de societăți.

### APAPR
- `https://apapr.ro/utile/` e accesibilă și conține linkuri către `P2.xlsx` / `P3.xlsx`, dar calea
  include anul și luna încărcării în WordPress, care se schimbă — **URL-ul trebuie extras prin
  parsarea paginii, nu ghicit**.
- Valorile coincid exact cu ASF pentru decembrie 2025, dar fișierul APAPR e **învechit cu ~8 luni**.
  Bun pentru validare încrucișată, nu ca sursă curentă.

---

## 4. Golurile rămase

- **Nu există serie lunară românească despre activitatea sau soliditatea asigurătorilor.** Singurul
  indicator lunar disponibil e prețul polițelor în IAPC. Cauza: raportarea Solvency II e trimestrială
  prin construcție, iar ASF nu publică nimic lunar și automatizabil.
- **Volumul pieței RCA** — cea mai relevantă cifră pentru publicul român — nu e disponibil din surse
  automatizabile. ASF îl publică doar în PDF-uri trimestriale cu nume de fișier de tip hash, în
  spatele WAF-ului.
- **Credite neperformante, solvabilitate, ROE/ROA pe sistemul bancar** — nu sunt în MIR/BSI; sursa ar
  fi BNR (blocat) sau ECB CBD2 (nu acoperă România).
- **Soldurile bancare în lei** — BCE publică doar în euro.
- **IRCC** — indicele la care sunt indexate creditele noi în lei nu există în nicio sursă
  internațională.
- **Cote de piață pe bancă, număr de unități, ATM-uri, conturi și carduri** — inexistente la nivel de
  bancă în sursele europene.
- **Emisiunile de titluri de stat pe piața primară** (randamente și sume adjudecate la licitațiile MF)
  — mfinante.gov.ro nu răspunde prin proxy.
- **Deținerile nerezidenților în titluri de stat** — doar la BNR.
- **Structura activelor financiare ale gospodăriilor rămâne trimestrială** — nu există echivalent
  lunar în regulamentul SEC 2010.
- **Pilonul I (pensii publice)** nu are echivalent pe `data.asfromania.ro`; CNPP rămâne inaccesibil.
- **Material neexploatat, suficient pentru încă 2 seturi:** ASF `p2`, tabelele 16–18 (plăți din fond,
  număr de plăți, conturi închise, pe tipuri — subiect de actualitate, faza de plată a Pilonului II)
  și tabelele 3, 8–14 (structura pe gen și vârstă, conturi fără contribuții, repartizare aleatorie,
  transferuri între fonduri).

---

## 5. Indici proprii propuși prin scraping lunar

`robots.txt` a fost verificat efectiv pentru fiecare propunere; site-urile netestate nu apar în listă.

### Piața de capital
1. **Compoziția și ponderile indicelui BET** — `bvb.ro/FinancialInstruments/Indices/IndicesProfiles.aspx?i=BET`.
   Fără `robots.txt` (404). Tabele ASP.NET randate pe server, citibile cu `pandas.read_html`.
   Produce un indice propriu de **concentrare a bursei** (Herfindahl pe ponderi) și rotația
   componentelor. **Efort: mic.**
2. **Indicatorii per emitent din secțiunea E.1 a buletinului lunar BVB** — aceeași sursă PDF deja
   folosită, paginile 7–10. Ar da numărul de emitenți activi, capitalizarea pe emitent, concentrarea
   top-10 și PER/DIVY pe companie, pe o serie de 200 de luni. **Efort: mediu.**
3. **Intercapital Research** — `intercapital.ro`, `robots.txt` complet permisiv. Estimări de consens
   și rapoarte de analiză pe emitenții mari; singura sursă românească deschisă de acest tip găsită
   funcțională. **Efort: mediu.**

### Bănci
4. **Indicele dobânzilor la depozite și al DAE afișate** — `bancatransilvania.ro/economii-si-investitii/dobanzi`
   și `/credite/credite-de-nevoi/exemple-reprezentative`; `robots.txt` conține explicit
   `User-agent: ClaudeBot → Allow: /`, `Crawl-delay: 5`. Valorile sunt randate pe server. Permite un
   indicator lunar de **decalaj între DAE și dobânda nominală afișată**, complementar setului 02 01.
   **Efort: mic.**
5. **Index comparativ multi-bancă** — `conso.ro/compara/depozite`; `robots.txt`: `Allow: /`,
   `Disallow: /api/`. Pagina întoarce HTML randat pe server cu dobânzi; `/api/` e interzis explicit și
   trebuie evitat. Ar acoperi golul „solduri și dobânzi în lei" lăsat de BCE. **Efort: mic-mediu.**
6. **Indice de rețea bancară (unități + bancomate)** — `bancatransilvania.ro/unitati-si-bancomate`,
   permis de `robots.txt`, dar datele vin dintr-un endpoint intern și cer randare headless. Ar produce
   un **indice lunar de contracție a rețelei bancare**, inexistent public. **Efort: mediu.**

### Asigurări
7. **Indicele UNSAR al daunelor comunicate** — `unsar.ro`, `robots.txt` interzice doar `/wp-admin/`;
   `wp-json/wp/v2/posts` întoarce JSON valid și actualizat. Extragere lunară a sumelor din comunicate,
   clasificate pe risc. **Efort: mic.** Limitare: serie condusă de evenimente, nu indice continuu.
8. **Indicele FGA al întârzierii despăgubirilor** — `fgaromania.ro`, `robots.txt` blochează doar un
   director de formulare; `wp-json` funcțional. Indicele ar urmări **decalajul în zile** dintre data
   publicării și data până la care sunt alocate cererile de plată pentru Euroins și City Insurance —
   măsură directă a întârzierii despăgubirilor post-faliment. **Efort: mic-mediu.**
9. **Monitor de disponibilitate a rapoartelor ASF** — testează lunar dacă apare un director
   `asigurari/` pe `data.asfromania.ro` (unde `pensii/` funcționează deja) și alertează când golul se
   închide. Nu produce date azi, dar **închide automat cel mai important gol al secțiunii** când ASF
   publică. **Efort: foarte mic.**

### Investiții și pensii
10. **Indicele fondurilor mutuale** — `tradeville.ro/fonduri-mutuale`; `robots.txt` interzice doar
    `/admin/`, `/cdn-cgi/`, `/chat/`, `/others/`, iar `sitemap_fonduri_mutuale.xml` listează 52 de
    pagini de fonduri. Conținut randat în JS, deci necesită Playwright. Ar da VUAN și randamente
    comparabile între administratori — exact ce s-a pierdut prin moartea aaf.ro. **Efort: mediu-mare.**
11. **Indicele de colectare a contribuțiilor la Pilonul II** — din `apapr.ro/utile/` → `P2.xlsx`, foaia
    `contributii`: raportul dintre contribuția efectiv colectată și cea teoretică, lunar. **Efort: mic.**
12. **Indicele 24reco al pensiei private (2008 = 100)** — din fișierele ASF deja descărcate: activul
    mediu per participant în lei și în euro, plus **randamentul real**, obținut prin deflatarea VUAN cu
    IAPC-ul din setul 03 01. **Efort: mic**, reutilizează codul existent.
13. **Monitor de rectificări ASF** — re-descarcă lunar `p2`/`p3` și detectează **modificările
    retroactive** ale valorilor deja publicate, producând un indice de revizuire. **Efort: mic.**

**Nu se scrapează:** `undelucram.ro` (`User-agent: ClaudeBot / Disallow: /`), `patriabank.ro`
(interzice explicit GPTBot, Google-Extended, CCBot), `compari.ro` (interzice tocmai paginile filtrate
după preț), `booking.com` (ToS-ul interzice contractual colectarea). Comparatoarele de RCA de tip
calculator (`rcaieftin.ro`) au `robots.txt` permisiv, dar interogarea repetată a calculatorului cu
profiluri sintetice depășește ce acoperă `robots.txt` — de făcut doar cu acordul operatorului.

---

## 6. Verificări făcute

- **Structură:** toate cele 20 de fișiere Excel se deschid, au foile `Sursa` și `Date` și 6–9 foi de
  analiză, cu câmpurile obligatorii completate în `Sursa`.
- **Randare:** toate cele 20 de pagini randate headless din `file://` — toate graficele desenate
  efectiv (nu doar canvas prezent), zero erori de consolă, zero derapaj orizontal la 390 px, zero
  apeluri `fetch()` pentru date.
- **Audit independent:** un agent separat a re-verificat toate cele ~78 de valori de titlu față de
  datele din Excel, a refăcut apeluri live la 13 surse și a recalculat variații, medii mobile,
  structuri procentuale și CAGR-uri. A găsit 4 erori reale — toate corectate și reverificate:
  un numitor greșit la un indicator din `04 03`, o afirmație contrazisă de propriile date în același
  set, 697 de rânduri etichetate greșit în `04 04` și o divergență de titlu între Excel și HTML în
  `05 03`.
- **Coerență între seturi:** activul Pilonului II este identic în `05 01`, `05 02` și `05 03`;
  depozitele populației sunt identice în `02 03` și `04 02`; ROBOR este identic în `01 04` și `02 04`;
  capitalizarea BVB e identică în `01 02` și `01 05`.
- **Reproductibilitate:** scripturi rulate cap-coadă din stare curată, cu cache gol — ieșirile
  identice cu livrabilele.
- **Fabricare:** nicio lună completată artificial, nicio interpolare. Stagnările lungi din serii au
  fost verificate individual la sursă și sunt reale.
