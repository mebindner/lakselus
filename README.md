# Lakselus i norsk havbrug – ugebrief og prognose på åbne data

Hvor mange voksne hunlus sidder der på laksen i Norges havbrug, hvordan udvikler det sig gennem året,
og kan man forudsige niveauet 1–4 uger frem bedre end en simpel tommelfingerregel?

Projektet henter ugentlige lusetællinger fra over 1.200 lokaliteter (2019 → i dag), samler dem pr.
produktionsområde og præsenterer dem i en Streamlit-app bygget som en ugentlig konsulentrapport.
Prognoserne bliver ærligt evalueret mod naive baselines.

Bygget i **Python** (pandas, Altair, pydeck/deck.gl, Streamlit). Privat porteføljeprojekt – uafhængig
analyse på åbne data, ikke udarbejdet for eller af nogen virksomhed.

## Appen – tre sider

### 1. Oversigt – ugebrief i konsulentformat
Opbygget som en rapportleverance:

- **Handlingstitel**, der siger konklusionen (fx *"Lusenivået er 24 % lavere end for et år siden – presset er størst i Karmøy til Sotra"*). Titler og tal beregnes fra data og følger med hver ny uge.
- **Executive summary** med tre nøglefund: kystens gennemsnit, lokaliteter over lusegrænsen og områder med rødt trafiklys.
- **Nummererede figurer** med enhed og kildeangivelse:
  1. Kort over lokaliteter og produktionsområder (farvet efter myndighedernes trafiklys) og rangering af de 13 områder mod lusegrænsen.
  2. Statustabel pr. område: lusetal, udvikling over 4 uger, andel over grænsen, havtemperatur.
  3. Små multipler: indeværende år mod snit og spænd for tidligere år, pr. område.
  4. Sæsonheatmap: toppen kommer senere, jo længere nordpå man kommer.
- **Metode og forbehold** nederst. Konklusioner bygger kun på områder med mindst 10 lokaliteter; små områder vises, men markeres.

### 2. Tidsmaskine – 3D-kort uge for uge
Et 3D-kort, hvor hver lokalitet er en søjle, der vokser med antal hunlus. Afspil perioden fra 2019 til
i dag og se lusene bygge sig op i sensommeren og falde igen om vinteren. Med tidslinje, hastighed og
mulighed for at dreje og vippe kortet.

Hele afspilningen kører i browseren: ~1.000 lokaliteter × ~400 uger pakkes som én byte pr. værdi
(≈ 0,6 MB) og tegnes med deck.gl. Kystlinjen er tegnet fra Natural Earth, så der kræves ingen kortnøgle.

### 3. Prognose – med ærlig evaluering
Vælg et produktionsområde og se de seneste tre år, prognosen 1–4 uger frem og en backtest af,
hvor præcise prognoserne har været.

## Evaluering

Rullende backtest (expanding window) fra januar 2023: hver uge forudsiges 1–4 uger frem **kun med
data, der fandtes på det tidspunkt**. Fejlmål er gennemsnitlig absolut fejl (MAE) i voksne hunlus pr. fisk.

| Horisont | Naiv (sidste uge) | Sæson-naiv (samme uge sidste år) |
|---|---|---|
| 1 uge | **0,025** | 0,061 |
| 2 uger | **0,034** | 0,061 |
| 3 uger | **0,043** | 0,061 |
| 4 uger | **0,047** | 0,061 |

Den naive baseline er klart stærkest: lusetallet ændrer sig langsomt fra uge til uge, mens sidste års
niveau er en dårlig rettesnor. Det er den, en egentlig model skal slå.

**Status:** Baselines og backtest er færdige. Selve modellen er under udvikling i
[`analyse/01_data_og_baselines.ipynb`](analyse/01_data_og_baselines.ipynb) og kommer på siden, når
den slår den naive baseline.

## Data

- **Kilde:** [BarentsWatch Fishhealth API](https://www.barentswatch.no/bwapi/openapi/) – bulk-eksporten
  af ugentlige lusetællinger pr. lokalitet med havtemperatur og produktionsområde, samt
  produktionsområdernes omrids og trafiklys.
- **Licens:** NLOD (Norsk lisens for offentlige data). Data levert av BarentsWatch; informasjon om lus
  er levert av Mattilsynet.
- **Behandling:** Områdetal er uvægtede gennemsnit over lokaliteter, der har talt lus i ugen (antal fisk
  pr. lokalitet er ikke med i datasættet). Den nyeste uge medtages først, når mindst 80 % af
  lokaliteterne har indberettet.

## Kom i gang

1. Opret bruger og API-klient på <https://www.barentswatch.no/minside/> (vælg **API-klient**).
   Klient-id har formen `din@email.dk:klientnavn`.
2. Kopiér `.env.example` til `.env` og udfyld `BW_CLIENT_ID` og `BW_CLIENT_SECRET`.
   `.env` er i `.gitignore` og må aldrig committes.
3. Installér, hent data og start appen:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m lakselus.hent --fra 2019
streamlit run app.py
```

Kør tests med `pytest`.

## Struktur

```
app.py                     navigation og fælles layout
sider/
  oversigt.py              ugebrief: resumé, figur 1–4, metode
  tidsmaskine.py           3D-kort afspillet uge for uge
  prognose.py              prognose og backtest pr. område
src/lakselus/
  barentswatch.py          API-klient (OAuth2 client credentials)
  hent.py                  henter rådata til lokal cache
  data.py                  dataklargøring: ugentligt panel pr. område
  evaluering.py            baselines, rullende backtest, MAE og skill
  appdata.py               cachede opslag og nøgletal til appen
  tidsmaskine.py/.html     datapakning og deck.gl-visning
  udseende.py              designsystem: farver, typografi, figurer, Altair-tema
analyse/                   notebook med dataklargøring, baselines og egen model
data/raw/                  lokal cache af rådata (ikke i git)
tests/
```
