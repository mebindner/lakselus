"""Skriver kompakte app-data til data/app, som committes og bruges af den hostede app.

Kør efter `python -m lakselus.hent` og `python -m lakselus.modelrapport`:  python -m lakselus.publicer

Indhold
1. Lusetal            – kun lokaliteter, der har talt, og kun de kolonner appen bruger
2. Behandlinger       – allerede samlet pr. område og uge, så filen er lille
3. Behandlingseffekt  – hændelsesstudiet af behandlingernes effekt (kræver behandlinger pr. lokalitet)
4. Produktionsområder – kopieres uændret
"""

import shutil

from lakselus import behandlingseffekt, data
from lakselus.config import DATA_APP, DATA_RAW

# Kun de kolonner og rækker, appen bruger: lokaliteter, der har talt lus.
KOLONNER = ["aar", "uge", "uge_start", "lokalitet", "lokalitet_navn", "hunlus", "temp", "har_talt",
            "over_graense", "omraade", "omraade_navn", "lat", "lon", "n_lok", "Lusegrense uke"]


def main() -> None:
    DATA_APP.mkdir(parents=True, exist_ok=True)

    # --- 1. Lusetal ------------------------------------------------------------------------
    raa = data.indlaes_raa()
    talt = raa[raa["har_talt"] == "Ja"]
    ud = talt[[k for k in KOLONNER if k in talt.columns]].copy()
    for k in ("hunlus", "temp", "lat", "lon"):
        ud[k] = ud[k].astype("float32")
    for k in ("lokalitet_navn", "omraade_navn", "har_talt", "over_graense", "Lusegrense uke"):
        if k in ud:
            ud[k] = ud[k].astype(str).astype("category")
    ud.to_parquet(data.APP_LUSETAL, index=False, compression="zstd")
    print(f"Skrev {data.APP_LUSETAL.name} ({len(ud):,} rækker, {data.APP_LUSETAL.stat().st_size / 1e6:.1f} MB)")

    # --- 2. Behandlinger -------------------------------------------------------------------
    beh = data.indlaes_behandlinger()
    if beh is not None:
        beh.to_parquet(data.APP_BEHANDLINGER, index=False, compression="zstd")
        print(f"Skrev {data.APP_BEHANDLINGER.name} ({len(beh):,} område-uger)")

    # --- 3. Behandlingseffekt --------------------------------------------------------------
    beh_raa = data.indlaes_behandlinger_raa()
    if beh_raa is not None:
        effekt = behandlingseffekt.effekt_tabel(raa, beh_raa)
        effekt.to_parquet(behandlingseffekt.APP_FIL, index=False)
        print(f"Skrev {behandlingseffekt.APP_FIL.name} ({effekt['type'].nunique()} behandlingstyper)")

    # --- 4. Produktionsområder -------------------------------------------------------------
    shutil.copyfile(DATA_RAW / "produktionsomraader.csv", data.APP_PRODUKTIONSOMRAADER)
    print(f"Skrev {data.APP_PRODUKTIONSOMRAADER.name}")


if __name__ == "__main__":
    main()
