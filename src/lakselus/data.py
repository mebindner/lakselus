"""Dataklargøring: fra rå tællinger og behandlinger pr. lokalitet til ugentligt panel pr. produktionsområde.

Indhold
1. Filer og kolonnenavne
2. Lusetal          – indlæsning og frasortering af uger, der stadig indberettes
3. Behandlinger     – antal behandlede lokaliteter pr. område og uge
4. Ugentligt panel  – ét komplet ugegitter pr. område, som modellerne bygger på
5. Områdenavne
"""

import pandas as pd

from lakselus.config import DATA_APP, DATA_RAW


# --- 1. Filer og kolonnenavne --------------------------------------------------------------

# Kompakte app-data (skrives af `python -m lakselus.publicer`), som den hostede app bruger uden API-nøgle.
APP_LUSETAL = DATA_APP / "lusetal.parquet"
APP_BEHANDLINGER = DATA_APP / "behandlinger.parquet"
APP_PRODUKTIONSOMRAADER = DATA_APP / "produktionsomraader.csv"

KOLONNER = {
    "År": "aar",
    "Uke": "uge",
    "Lokalitetsnummer": "lokalitet",
    "Voksne hunnlus": "hunlus",
    "Lus i bevegelige stadier": "mob",
    "Fastsittende lus": "fast",
    "Sjøtemperatur": "temp",
    "Har telt lakselus": "har_talt",
    "ProduksjonsområdeId": "omraade",
    "Produksjonsområde": "omraade_navn",
    "Lokalitetsnavn": "lokalitet_navn",
    "Over lusegrense uke": "over_graense",
    "Lat": "lat",
    "Lon": "lon",
}


def _uge_start(aar: pd.Series, uge: pd.Series) -> pd.Series:
    """Mandagen i ISO-ugen – fælles tidsnøgle for alle datasæt."""
    return pd.to_datetime(aar.astype(str) + "-W" + uge.astype(str).str.zfill(2) + "-1", format="%G-W%V-%u")


# --- 2. Lusetal ----------------------------------------------------------------------------

def indlaes_raa() -> pd.DataFrame:
    """Alle cachede år samlet, med korte danske kolonnenavne.

    Lokalt læses rådata fra data/raw. Findes de ikke (fx på Streamlit Cloud), bruges den kompakte
    udgave i data/app, som `python -m lakselus.publicer` skriver.
    """
    filer = sorted(DATA_RAW.glob("lusetal_*.csv"))
    if not filer:
        if APP_LUSETAL.exists():
            app = pd.read_parquet(APP_LUSETAL)
            tekst = app.select_dtypes("category").columns  # kategorier gemmes kompakt, men bruges som tekst
            tal = [k for k in ("hunlus", "mob", "fast", "temp", "lat", "lon") if k in app]
            return app.astype({k: str for k in tekst} | {k: "float64" for k in tal})
        raise FileNotFoundError("Ingen data i data/raw. Kør først: python -m lakselus.hent")
    raa = pd.concat((pd.read_csv(f, low_memory=False) for f in filer), ignore_index=True)
    raa = raa.rename(columns=KOLONNER)
    raa["uge_start"] = _uge_start(raa["aar"], raa["uge"])
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


# --- 3. Behandlinger -----------------------------------------------------------------------

def behandlinger_pr_omraade(beh: pd.DataFrame) -> pd.DataFrame:
    """Antal lokaliteter pr. (omraade, uge_start), der blev behandlet mod lus.

    n_beh: lokaliteter med mindst én behandling (alle typer). n_med: heraf med medicin (bad eller fôr).
    En lokalitet tæller én gang pr. uge, selv om den har flere behandlinger eller behandler flere merder.
    """
    beh = beh.assign(uge_start=_uge_start(beh["År"], beh["Uke"]),
                     med_lok=beh["Lokalitetsnummer"].where(beh["Tiltak"].eq("medikamentell")))
    agg = beh.groupby(["ProduksjonsområdeId", "uge_start"]).agg(
        n_beh=("Lokalitetsnummer", "nunique"), n_med=("med_lok", "nunique"))
    return agg.rename_axis(["omraade", "uge_start"]).reset_index().astype({"omraade": int})


def indlaes_behandlinger_raa() -> pd.DataFrame | None:
    """Alle behandlinger pr. lokalitet (én række pr. behandling) fra data/raw. None uden rådata."""
    filer = sorted(DATA_RAW.glob("behandlinger_*.csv"))
    return pd.concat((pd.read_csv(f) for f in filer), ignore_index=True) if filer else None


def indlaes_behandlinger() -> pd.DataFrame | None:
    """Behandlinger pr. område og uge – fra rådata, ellers fra app-data. None, hvis ingen findes."""
    raa = indlaes_behandlinger_raa()
    if raa is not None:
        return behandlinger_pr_omraade(raa)
    if APP_BEHANDLINGER.exists():
        return pd.read_parquet(APP_BEHANDLINGER)
    return None


# --- 4. Ugentligt panel --------------------------------------------------------------------

def ugentligt_panel(raa: pd.DataFrame, behandlinger: pd.DataFrame | None = None) -> pd.DataFrame:
    """Ét rækkesæt pr. (omraade, uge_start) på et komplet ugegitter.

    hunlus = uvægtet gennemsnit af voksne hunlus pr. fisk over lokaliteter, der har talt den uge.
    mob og fast = det samme for bevægelige og fastsiddende lus – de yngre stadier, der bliver voksne hunlus.
    Uger uden tællinger i et område står som NaN (gitteret er komplet, så shift(k) = k uger tilbage).
    Med `behandlinger` får panelet også n_beh og n_med (0 i uger uden indberettede behandlinger).
    """
    talt = raa[(raa["har_talt"] == "Ja") & raa["omraade"].notna()].copy()
    talt["omraade"] = talt["omraade"].astype(int)
    stadier = {k: (k, "mean") for k in ("mob", "fast") if k in talt}  # mangler i ældre app-data
    agg = talt.groupby(["omraade", "uge_start"]).agg(
        hunlus=("hunlus", "mean"),
        **stadier,
        temp=("temp", "mean"),
        n_lok=("lokalitet", "nunique"),
    )
    uger = pd.date_range(talt["uge_start"].min(), talt["uge_start"].max(), freq="W-MON")
    gitter = pd.MultiIndex.from_product([sorted(talt["omraade"].unique()), uger], names=agg.index.names)
    panel = agg.reindex(gitter).reset_index()
    panel["n_lok"] = panel["n_lok"].fillna(0).astype(int)
    if behandlinger is not None:
        b = behandlinger.set_index(["omraade", "uge_start"])[["n_beh", "n_med"]]
        panel = panel.join(b, on=["omraade", "uge_start"])
        panel[["n_beh", "n_med"]] = panel[["n_beh", "n_med"]].fillna(0).astype(int)
    return panel


# --- 5. Områdenavne ------------------------------------------------------------------------

# Officielle navne (Fiskeridirektoratet), hvor BarentsWatchs to kilder staver forskelligt:
# lusetallene skriver "Nordhordaland", områdelisten "Ryfylket".
RETTEDE_NAVNE = {2: "Ryfylke", 4: "Nordhordland til Stadt"}


def omraade_navne(raa: pd.DataFrame) -> dict[int, str]:
    navne = raa.dropna(subset=["omraade"]).drop_duplicates("omraade")
    return dict(zip(navne["omraade"].astype(int), navne["omraade_navn"])) | RETTEDE_NAVNE
