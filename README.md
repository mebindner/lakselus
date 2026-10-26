# Lakselus – forecast på åbne norske data

Hvor mange voksne hunlus sidder der på laksen om 1–4 uger? Projektet forudsiger det
gennemsnitlige antal voksne hunlus pr. fisk for hvert af Norges 13 produktionsområder
og viser **ærligt**, om modellen faktisk slår en simpel baseline.

Bygget i Python med en Streamlit-side. Privat porteføljeprojekt.

## Data

- **Kilde:** [BarentsWatch Fishhealth API](https://www.barentswatch.no/bwapi/openapi/) –
  bulk-eksporten `/v1/geodata/download/fishhealth?reporttype=lice` giver ugentlige
  lusetællinger pr. lokalitet med havtemperatur og produktionsområde (data fra 2012).
- **Produktionsområder:** `/v1/geodata/productionarea` (1–13).
- **Licens:** NLOD (Norsk lisens for offentlige data). Data levert av BarentsWatch;
  lusedata er levert av Mattilsynet.

## Plan (bevidst lille)

| Del | Valg |
|---|---|
| Datakilde | Én: BarentsWatch lusetællinger 2019→ i dag |
| Mål | Ugentligt gns. voksne hunlus pr. produktionsområde (vægtet over aktive lokaliteter) |
| Baselines | Naiv (sidste uge) og sæson-naiv (samme uge sidste år) |
| Model | Én: gradient boosting / lineær model på lags + uge-sæson + havtemperatur |
| Evaluering | Rullende backtest (expanding window) på 2023–2025, horisont 1–4 uger, MAE pr. område og horisont, og skill = 1 − MAE_model / MAE_naiv |
| Side | Én Streamlit-side: vælg område → historik, forecast med usikkerhed, backtest-tabel |

## Kom i gang

1. Opret bruger og API-klient på <https://www.barentswatch.no/minside/>
   (vælg **API-klient**). Klient-id har formen `din@email.dk:klientnavn`.
2. Kopiér `.env.example` til `.env` og udfyld `BW_CLIENT_ID` og `BW_CLIENT_SECRET`.
   `.env` er i `.gitignore` og må aldrig committes.
3. Installér og kør:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m lakselus.hent --fra 2019
streamlit run app.py
```

## Struktur

```
src/lakselus/   API-klient, datahentning (senere: features, model, evaluering)
analyse/        notebooks til udforskning
data/raw/       lokal cache af rådata (ikke i git)
app.py          Streamlit-siden
tests/
```
