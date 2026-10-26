"""Dataklargøring: fra rå lusetællinger pr. lokalitet til ugentligt panel pr. produktionsområde."""

import pandas as pd

from lakselus.config import DATA_RAW

KOLONNER = {
    "År": "aar",
    "Uke": "uge",
    "Lokalitetsnummer": "lokalitet",
    "Voksne hunnlus": "hunlus",
    "Sjøtemperatur": "temp",
    "Har telt lakselus": "har_talt",
    "ProduksjonsområdeId": "omraade",
    "Produksjonsområde": "omraade_navn",
    "Lokalitetsnavn": "lokalitet_navn",
    "Over lusegrense uke": "over_graense",
    "Lat": "lat",
    "Lon": "lon",
}


def indlaes_raa() -> pd.DataFrame:
    """Alle cachede år samlet, med korte danske kolonnenavne."""
    filer = sorted(DATA_RAW.glob("lusetal_*.csv"))
    if not filer:
        raise FileNotFoundError("Ingen data i data/raw. Kør først: python -m lakselus.hent")
    raa = pd.concat((pd.read_csv(f, low_memory=False) for f in filer), ignore_index=True)
    raa = raa.rename(columns=KOLONNER)
    raa["uge_start"] = pd.to_datetime(
        raa["aar"].astype(str) + "-W" + raa["uge"].astype(str).str.zfill(2) + "-1", format="%G-W%V-%u"
    )
    return fjern_ufaerdige_uger(raa)


def fjern_ufaerdige_uger(raa: pd.DataFrame, andel: float = 0.8) -> pd.DataFrame:
    """Dropper de sidste uger, hvor indberetningen ikke er færdig endnu.

    Lusetal indberettes i ugen efter, så den nyeste uge har ofte kun en del af lokaliteterne.
    En uge regnes som færdig, når antal lokaliteter der har talt er mindst `andel` af medianen for de 8 uger før.
    """
    antal = raa[raa["har_talt"] == "Ja"].groupby("uge_start").size()
    while len(antal) > 8 and antal.iloc[-1] < andel * antal.iloc[-9:-1].median():
        antal = antal.iloc[:-1]
    return raa[raa["uge_start"] <= antal.index[-1]]


def ugentligt_panel(raa: pd.DataFrame) -> pd.DataFrame:
    """Ét rækkesæt pr. (omraade, uge_start) på et komplet ugegitter.

    hunlus = uvægtet gennemsnit af voksne hunlus pr. fisk over lokaliteter, der har talt den uge.
    Uger uden tællinger i et område står som NaN (gitteret er komplet, så shift(k) = k uger tilbage).
    """
    talt = raa[(raa["har_talt"] == "Ja") & raa["omraade"].notna()].copy()
    talt["omraade"] = talt["omraade"].astype(int)
    agg = talt.groupby(["omraade", "uge_start"]).agg(
        hunlus=("hunlus", "mean"),
        temp=("temp", "mean"),
        n_lok=("lokalitet", "nunique"),
    )
    uger = pd.date_range(talt["uge_start"].min(), talt["uge_start"].max(), freq="W-MON")
    gitter = pd.MultiIndex.from_product([sorted(talt["omraade"].unique()), uger], names=agg.index.names)
    panel = agg.reindex(gitter).reset_index()
    panel["n_lok"] = panel["n_lok"].fillna(0).astype(int)
    return panel


def omraade_navne(raa: pd.DataFrame) -> dict[int, str]:
    navne = raa.dropna(subset=["omraade"]).drop_duplicates("omraade")
    return dict(zip(navne["omraade"].astype(int), navne["omraade_navn"]))
