"""Skriver kompakte app-data til data/app, som committes og bruges af den hostede app.

Kør efter `python -m lakselus.hent` og `python -m lakselus.modelrapport`:  python -m lakselus.publicer
"""

import shutil

from lakselus import data
from lakselus.config import DATA_APP, DATA_RAW

# Kun de kolonner og rækker, appen bruger: lokaliteter, der har talt lus.
KOLONNER = ["aar", "uge", "uge_start", "lokalitet", "lokalitet_navn", "hunlus", "temp", "har_talt",
            "over_graense", "omraade", "omraade_navn", "lat", "lon", "n_lok"]


def main() -> None:
    raa = data.indlaes_raa()
    talt = raa[raa["har_talt"] == "Ja"]
    ud = talt[[k for k in KOLONNER if k in talt.columns]].copy()
    for k in ("hunlus", "temp", "lat", "lon"):
        ud[k] = ud[k].astype("float32")
    for k in ("lokalitet_navn", "omraade_navn", "har_talt", "over_graense"):
        ud[k] = ud[k].astype("category")
    DATA_APP.mkdir(parents=True, exist_ok=True)
    ud.to_parquet(data.APP_LUSETAL, index=False, compression="zstd")
    shutil.copyfile(DATA_RAW / "produktionsomraader.csv", data.APP_PRODUKTIONSOMRAADER)
    print(f"Skrev {data.APP_LUSETAL.name} ({len(ud):,} rækker, {data.APP_LUSETAL.stat().st_size / 1e6:.1f} MB) "
          f"og {data.APP_PRODUKTIONSOMRAADER.name}")


if __name__ == "__main__":
    main()
