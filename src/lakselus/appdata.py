"""Cachede dataopslag, som deles af siderne i Streamlit-appen.

Indhold
1. Indlæsning           – lusetal, behandlinger og panel; cachen fornyes, når datafilerne ændres
2. Produktionsområder   – omrids og trafiklys, slået op for den viste uge
3. Opdateringsstatus    – hvornår data sidst blev opdateret, og hvornår næste opdatering kommer
4. Nøgletal (Overview)  – status pr. område og sæsonprofil
5. Modeller (Forecast)  – backtest, opsummering og live-prognose (læses fra disk, når de er friske)
6. Behandlingseffekt     – hændelsesstudiet til Forecast-siden
"""

import ast

import pandas as pd
import streamlit as st

from lakselus import behandlingseffekt, data
from lakselus.config import DATA_RAW
from lakselus.data import APP_PRODUKTIONSOMRAADER

TRAFIKLYS = {"green": "Green", "yellow": "Yellow", "red": "Red"}


# --- 1. Indlæsning --------------------------------------------------------------------------

def data_version() -> float:
    """Seneste ændringstid for datafilerne.

    Bruges som cache-nøgle: appen holdes vågen og genstarter sjældent, så uden den ville en ugentlig
    opdatering (nye filer via git push) aldrig blive indlæst – cachen ville vise de gamle tal.
    """
    filer = [*DATA_RAW.glob("*.csv"), data.APP_LUSETAL, data.APP_BEHANDLINGER, behandlingseffekt.APP_FIL,
             APP_PRODUKTIONSOMRAADER]
    return max((f.stat().st_mtime for f in filer if f.exists()), default=0.0)


def indlaes():
    return _indlaes(data_version())


@st.cache_data(show_spinner="Loading lice counts …", max_entries=2)
def _indlaes(version: float):
    raa = data.indlaes_raa()
    return raa, data.ugentligt_panel(raa, data.indlaes_behandlinger()), data.omraade_navne(raa)


# --- 2. Produktionsområder ------------------------------------------------------------------

def omraader() -> pd.DataFrame:
    return _omraader(data_version())


@st.cache_data(max_entries=2)
def _omraader(version: float) -> pd.DataFrame:
    """Produktionsområder med omrids (lon/lat-polygon) og gældende trafiklysfarve."""
    fil = DATA_RAW / "produktionsomraader.csv"
    po = pd.read_csv(fil if fil.exists() else APP_PRODUKTIONSOMRAADER)
    po["polygon"] = po["geometry.coordinates"].map(lambda s: ast.literal_eval(s)[0])
    po["lys_historik"] = po["colors"].map(ast.literal_eval)
    po["trafiklys"] = po["lys_historik"].map(lambda h: h[-1]["color"])
    po["name"] = [data.RETTEDE_NAVNE.get(i, n) for i, n in zip(po["id"], po["name"])]
    return po[["id", "name", "polygon", "trafiklys", "lys_historik"]].rename(columns={"id": "omraade", "name": "navn"})


def trafiklys_paa(po: pd.DataFrame, dato: pd.Timestamp) -> pd.DataFrame:
    """Trafiklysfarven, der gjaldt på datoen, og hvornår den blev besluttet.

    Regeringen fastsætter farven hvert andet år ud fra beregnet lusedødelighed hos vild laks – ikke ud fra
    ugens lusetal på anlæggene. Farven slås op for den viste uge, så en ældre uge ikke får en senere beslutning.
    """
    def opslag(historik: list[dict]) -> tuple[str, pd.Timestamp]:
        for p in reversed(historik):
            fra = pd.Timestamp(p["fromDate"]).tz_localize(None)
            if fra <= dato:
                return p["color"], fra
        return historik[0]["color"], pd.Timestamp(historik[0]["fromDate"]).tz_localize(None)

    lys = po["lys_historik"].map(opslag)
    return po.assign(trafiklys=lys.str[0], lys_fra=pd.to_datetime(lys.str[1]))


# --- 3. Opdateringsstatus -------------------------------------------------------------------

def opdatering(panel: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp | None]:
    """Hvornår data sidst blev opdateret, og hvornår næste opdatering kommer.

    Den ugentlige kørsel er onsdag i ugen efter den seneste komplette uge (uge_start er en mandag).
    Er næste dato overskredet, gives None, så appen ikke lover en dato, der allerede er gået.
    """
    sidst = panel["uge_start"].max() + pd.Timedelta(days=9)
    naeste = sidst + pd.Timedelta(weeks=1)
    i_dag = pd.Timestamp.now(tz="Europe/Oslo").tz_localize(None).normalize()
    return sidst, (naeste if i_dag <= naeste else None)


def opdatering_tekst(panel: pd.DataFrame) -> str:
    """Fx "Updated Wed 28 Oct 2026 · next update Wed 4 Nov"."""
    sidst, naeste = opdatering(panel)
    tekst = f"Updated {sidst.strftime('%a')} {sidst.day} {sidst.strftime('%b %Y')}"
    return tekst + (f" · next update {naeste.strftime('%a')} {naeste.day} {naeste.strftime('%b')}" if naeste is not None else "")


# --- 4. Nøgletal (Overview) -----------------------------------------------------------------

def status_pr_omraade(raa: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """Nøgletal pr. område for seneste uge: hunlus, trend mod 4 uger før, andel over grænsen, temperatur."""
    seneste = panel["uge_start"].max()
    talt = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] == seneste)]
    nu = talt.groupby("omraade").agg(
        hunlus=("hunlus", "mean"),
        temp=("temp", "mean"),
        n_lok=("lokalitet", "nunique"),
        andel_over=("over_graense", lambda s: (s == "Ja").mean()),
    )
    foer = panel[(panel["uge_start"] < seneste) & (panel["uge_start"] >= seneste - pd.Timedelta(weeks=4))]
    nu["hunlus_4u_foer"] = foer.groupby("omraade")["hunlus"].mean()
    nu.index = nu.index.astype(int)
    return nu


def saesonprofil(panel: pd.DataFrame) -> pd.DataFrame:
    """Lusetal pr. område og ISO-uge for indeværende år, holdt op mod spændet og snittet for tidligere år."""
    p = panel.dropna(subset=["hunlus"]).copy()
    iso = p["uge_start"].dt.isocalendar()
    p["aar"], p["uge"] = iso["year"].astype(int), iso["week"].astype(int)
    p = p[p["uge"] <= 52]
    i_aar = p["aar"].max()
    tidl = p[p["aar"] < i_aar].groupby(["omraade", "uge"])["hunlus"].agg(lav="min", hoej="max", snit="mean")
    nu = p[p["aar"] == i_aar].set_index(["omraade", "uge"])["hunlus"].rename("i_aar")
    return tidl.join(nu).reset_index().assign(aar=i_aar, foerste_aar=p["aar"].min())


# --- 5. Modeller (Forecast) -----------------------------------------------------------------

@st.cache_data(show_spinner="Running full backtest of all models (takes a few minutes the first time) …", max_entries=2)
def backtest_resultater(panel: pd.DataFrame) -> pd.DataFrame:
    """Backtest af alle modeller. Læses fra disk og genberegnes kun, når der er kommet nye uger."""
    from lakselus import modelrapport

    fil = modelrapport.BACKTEST_FIL
    if fil.exists():
        res = pd.read_parquet(fil)
        if res["origin"].max() >= panel["uge_start"].max() - pd.Timedelta(weeks=1):
            return res
    res = modelrapport.koer(panel, log=lambda *_: None)
    fil.parent.mkdir(parents=True, exist_ok=True)
    res.to_parquet(fil, index=False)
    return res


@st.cache_data(show_spinner=False, max_entries=2)
def model_opsummering(res: pd.DataFrame) -> dict:
    from lakselus import modelrapport

    return modelrapport.opsummer(res)


@st.cache_data(show_spinner="Training the selected model on all data …", max_entries=2)
def live_prognose(panel: pd.DataFrame, model: str, res: pd.DataFrame) -> pd.DataFrame:
    """Prognose 1–4 uger frem med 80 %-interval. Læses fra den ugentlige kørsel, hvis den passer til data."""
    from lakselus import modelrapport

    fil = modelrapport.PROGNOSE_FIL
    if fil.exists():
        gemt = pd.read_parquet(fil)
        if (gemt["model"] == model).all() and gemt["uge_start"].min() == panel["uge_start"].max() + pd.Timedelta(weeks=1):
            return gemt
    return modelrapport.live_prognose(panel, model, res)


# --- 6. Behandlingseffekt ------------------------------------------------------------------

def behandlingseffekt_tabel() -> pd.DataFrame | None:
    return _behandlingseffekt_tabel(data_version())


@st.cache_data(show_spinner=False, max_entries=2)
def _behandlingseffekt_tabel(version: float) -> pd.DataFrame | None:
    """Den publicerede tabel; lokalt beregnes den fra rådata, hvis den mangler. None uden behandlingsdata."""
    if behandlingseffekt.APP_FIL.exists():
        return pd.read_parquet(behandlingseffekt.APP_FIL)
    beh = data.indlaes_behandlinger_raa()
    return behandlingseffekt.effekt_tabel(data.indlaes_raa(), beh) if beh is not None else None
