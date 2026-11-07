# Site tour video (about 48 seconds)

Scripts that record the app and cut `video/lakselus-rundtur.mp4` (1080×1350, 30 fps) with a cover image
`video/lakselus-rundtur-cover.png`. Frames, log and the finished video are written to this folder and left out of git
(`.gitignore`).

The story: hook (the currents map) → Latest week (the coast and one farm) → Forecast → treatments → History →
Currents (finale) → About → end card.

## Requirements

- Google Chrome (Playwright uses `channel="chrome"`) and `ffmpeg` on the PATH.
- A Python environment with Playwright and Pillow:

  ```bash
  python3 -m venv video-venv && video-venv/bin/pip install playwright pillow
  ```

- The app running locally on port 8502 (`streamlit run app.py --server.port 8502`) with the data the video should show.

## Run in this order

1. **Record** – drives the app in headless Chrome and saves screenshots (`frames4/`) and `log4.json`
   (the mouse path, clicks, markers and where elements sit on the page). Takes just under two minutes.

   ```bash
   video-venv/bin/python video/optag.py
   ```

2. **Preview** (optional) – renders single frames to `ud4/b/` at the given times in seconds:

   ```bash
   video-venv/bin/python video/klip.py proeve 4 9.5 18 23.5 28.5 34 43 46.5
   ```

3. **Cut** – renders the whole video and joins it with ffmpeg into `video/lakselus-rundtur.mp4`. Takes a few minutes.

   ```bash
   video-venv/bin/python video/klip.py
   ```

4. **Cover image** – a frame from the hook:

   ```bash
   ffmpeg -y -ss 5.5 -i video/lakselus-rundtur.mp4 -frames:v 1 video/lakselus-rundtur-cover.png
   ```

## Captions with figures from the data

The captions live in `KAPITLER` in `klip.py` and must be checked against the app when the data is updated:

| Chapter | Caption | Where the figure comes from |
|---|---|---|
| Latest week | "**569** farms reported in week **44** – search any of **876**" | The header and search box on Latest week |
| The forecast | "**29%** lower error than naive" | Key figure 03 on Forecast (4 weeks ahead, test period) |
| Treatments | "Thermal: **87%** fewer lice than similar untreated farms within a week" | Exhibit 2 on Forecast |
| History | "2026 is still rising in week **44** – later than the usual peak" | The title of exhibit 1 on History |
| Currents | "about **7** km a day" | The headline on Currents |

## What can break with new data or layout changes

- `optag.py` searches for "Skorp", picks `"Skorpo · PO 3 · 25896"` and waits for `?site=25896`. If the farm
  disappears from the search box, choose another one (`ANLAEG` at the top of the file).
- The History caption only holds while 2026 keeps rising after the usual peak; if the page title changes, the caption
  must follow.
- The camera zoom in `klip.py` uses element positions from `log4.json`. If page layouts change – the Currents page has
  since gained a life cycle section below the map – check the frames with `proeve` before rendering the whole video.

Code identifiers and comments in the scripts are in Danish, like the rest of the project (see the glossary in the main
README).
