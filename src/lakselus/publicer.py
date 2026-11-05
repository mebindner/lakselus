"""Skriver kompakte app-data til data/app, som committes og bruges af den hostede app.

Kør efter `python -m lakselus.hent` og `python -m lakselus.modelrapport`:  python -m lakselus.publicer

Før noget skrives, kontrolleres de nye data mod de publicerede (afsnit 0). Ser noget forkert ud – færre uger,
langt færre rækker, urimelige lusetal eller manglende behandlinger – stopper kørslen med en fejl. Så pushes
intet, appen beholder de sidste gode data, og GitHub sender besked om den fejlede kørsel.

Indhold
0. Kvalitetskontrol   – nye data mod de publicerede
1. Lusetal            – kun lokaliteter, der har talt, og kun de kolonner appen bruger
2. Behandlinger       – allerede samlet pr. område og uge, så filen er lille
3. Behandlingseffekt  – hændelsesstudiet af behandlingernes effekt (kræver behandlinger pr. lokalitet)
4. Produktionsområder – kopieres uændret
"""

import shutil

import pandas as pd

from lakselus import behandlingseffekt, data
from lakselus.config import DATA_APP, DATA_RAW

# Kun de kolonner og rækker, appen bruger: lokaliteter, der har talt lus.
KOLONNER = ["aar", "uge", "uge_start", "lokalitet", "lokalitet_navn", "hunlus", "mob", "fast", "temp", "har_talt",
            "over_graense", "omraade", "omraade_navn", "lat", "lon", "n_lok", "Lusegrense uke"]


# --- 0. Kvalitetskontrol -------------------------------------------------------------------

MIN_LOKALITETER = 300   # lokaliteter, der har talt i seneste uge (normalt 500–600)
MIN_OMRAADER = 11       # områder med tællinger i seneste uge (PO 1 og 13 er små og kan mangle en uge)
MAKS_HUNLUS = 50.0      # højere værdier er tastefejl, ikke lus
MIN_ANDEL_RAEKKER = 0.95


def kvalitetstjek(ny: pd.DataFrame, gammel: pd.DataFrame | None, har_behandlinger: bool,
                  havde_behandlinger: bool) -> list[str]:
    """Problemer ved de nye lusetal (lokaliteter, der har talt) – tom liste, hvis alt ser rigtigt ud."""
    problemer = []
    seneste = ny["uge_start"].max()
    sidste_uge = ny[ny["uge_start"] == seneste]
    if sidste_uge["lokalitet"].nunique() < MIN_LOKALITETER:
        problemer.append(f"kun {sidste_uge['lokalitet'].nunique()} lokaliteter i seneste uge ({seneste:%Y-%m-%d})")
    if sidste_uge["omraade"].nunique() < MIN_OMRAADER:
        problemer.append(f"kun {sidste_uge['omraade'].nunique()} produktionsområder i seneste uge")
    hunlus = ny["hunlus"].dropna()
    if hunlus.empty or (hunlus < 0).any() or (hunlus > MAKS_HUNLUS).any():
        problemer.append(f"lusetal uden for 0–{MAKS_HUNLUS:g} pr. fisk")
    if gammel is not None and len(gammel):
        if seneste < gammel["uge_start"].max():
            problemer.append(f"seneste uge ({seneste:%Y-%m-%d}) er ældre end den publicerede "
                             f"({gammel['uge_start'].max():%Y-%m-%d})")
        if len(ny) < MIN_ANDEL_RAEKKER * len(gammel):
            problemer.append(f"{len(ny):,} rækker mod {len(gammel):,} publicerede")
    if havde_behandlinger and not har_behandlinger:
        problemer.append("behandlingsdata mangler, men er publiceret før")
    return problemer


def main() -> None:
    DATA_APP.mkdir(parents=True, exist_ok=True)
    raa = data.indlaes_raa()
    talt = raa[raa["har_talt"] == "Ja"]
    beh = data.indlaes_behandlinger()

    # --- 0. Kvalitetskontrol ---------------------------------------------------------------
    gammel = pd.read_parquet(data.APP_LUSETAL, columns=["uge_start"]) if data.APP_LUSETAL.exists() else None
    problemer = kvalitetstjek(talt, gammel, beh is not None, data.APP_BEHANDLINGER.exists())
    if problemer:
        raise SystemExit("Publicerer ikke – data ser forkerte ud:\n- " + "\n- ".join(problemer))

    # --- 1. Lusetal ------------------------------------------------------------------------
    ud = talt[[k for k in KOLONNER if k in talt.columns]].copy()
    for k in ("hunlus", "mob", "fast", "temp", "lat", "lon"):
        if k in ud:
            ud[k] = pd.to_numeric(ud[k], errors="coerce").astype("float32")
    for k in ("lokalitet_navn", "omraade_navn", "har_talt", "over_graense", "Lusegrense uke"):
        if k in ud:
            ud[k] = ud[k].astype(str).astype("category")
    ud.to_parquet(data.APP_LUSETAL, index=False, compression="zstd")
    print(f"Skrev {data.APP_LUSETAL.name} ({len(ud):,} rækker, {data.APP_LUSETAL.stat().st_size / 1e6:.1f} MB)")

    # --- 2. Behandlinger -------------------------------------------------------------------
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
