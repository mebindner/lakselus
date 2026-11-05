# Rundtur-videoen til LinkedIn (ca. 48 sek.)

Scripts, der optager appen og klipper `video/lakselus-rundtur.mp4` (1080×1350, 30 fps) med et forsidebillede
`video/lakselus-rundtur-cover.png`. Billeder, log og den færdige video skrives i denne mappe og er udeladt i `.gitignore`.

Fortællingen: krog (strømkortet) → Latest week (kysten og ét anlæg) → Forecast → behandlinger → History →
Currents (finale) → About → slutkort.

## Forudsætninger

- Google Chrome (Playwright bruger `channel="chrome"`) og `ffmpeg` på PATH.
- Et Python-miljø med Playwright og Pillow:

  ```bash
  python3 -m venv video-venv && video-venv/bin/pip install playwright pillow
  ```

- Appen kører lokalt på port 8502 (`streamlit run app.py --server.port 8502`) med de data, der skal med i videoen.

## Kør i denne rækkefølge

1. **Optag** – styrer appen i en headless Chrome og gemmer skærmbilleder (`frames4/`) og `log4.json`
   (musens bane, klik, markører og elementernes placering). Tager knap to minutter.

   ```bash
   video-venv/bin/python video/optag.py
   ```

2. **Prøv** (valgfrit) – tegner enkelte billeder til `ud4/b/` på de angivne tidspunkter i sekunder:

   ```bash
   video-venv/bin/python video/klip.py proeve 4 9.5 18 23.5 28.5 34 43 46.5
   ```

3. **Klip** – tegner hele videoen og samler den med ffmpeg til `video/lakselus-rundtur.mp4`. Tager et par minutter.

   ```bash
   video-venv/bin/python video/klip.py
   ```

4. **Forsidebillede** – et billede fra krogen:

   ```bash
   ffmpeg -y -ss 5.5 -i video/lakselus-rundtur.mp4 -frames:v 1 video/lakselus-rundtur-cover.png
   ```

## Tekster med tal fra data

Teksterne står i `KAPITLER` i `klip.py` og skal tjekkes mod appen, når data er opdateret:

| Kapitel | Tekst | Hvor tallet kommer fra |
|---|---|---|
| Latest week | "**569** farms reported in week **44** – search any of **876**" | Sidehovedet og søgefeltet på Latest week |
| The forecast | "**29%** lower error than naive" | Nøgletal 03 på Forecast (4 uger frem, testperioden) |
| Treatments | "Thermal: **87%** fewer lice than similar untreated farms within a week" | Figur 2 på Forecast |
| History | "2026 is still rising in week **44** – later than the usual peak" | Titlen på figur 1 på History |
| Currents | "about **7** km a day" | Overskriften på Currents |

## Ting, der kan gå i stykker ved nye data

- `optag.py` søger "Skorp" og vælger `"Skorpo · PO 3 · 25896"`, og den venter på `?site=25896`. Forsvinder
  anlægget fra søgefeltet, skal et andet vælges (`ANLAEG` øverst i filen).
- History-teksten passer kun, så længe 2026 stiger efter den sædvanlige top; skifter titlen på siden, skal teksten følge med.
- Kameraets zoom i `klip.py` bruger elementernes placering fra `log4.json`. Ændres sidernes layout,
  skal billederne tjekkes med `proeve`, før hele videoen tegnes.
