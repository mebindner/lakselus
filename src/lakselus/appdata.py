"""Cachede dataopslag, som deles af siderne i Streamlit-appen.

Indhold
1. Indlæsning           – lusetal, behandlinger og panel; cachen fornyes, når datafilerne ændres
2. Produktionsområder   – omrids og trafiklys, slået op for den viste uge
3. Opdateringsstatus    – hvornår data sidst blev opdateret, og hvornår næste opdatering kommer
4. Nøgletal (Overview)  – status pr. område og sæsonprofil
5. Modeller (Forecast)  – backtest, opsummering og live-prognose (læses fra disk, når de er friske)
6. Behandlingseffekt     – hændelsesstudiet til Forecast-siden
7. Opslag (Overview)     – søg område eller anlæg, valget i URL'en, anlæggets historik og naboer
8. Ugens udsving        – anlæg med det højeste lusetal og de største stigninger og fald (Overview)
"""

import ast
import math

import numpy as np
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



# --- 7. Opslag (Overview) ------------------------------------------------------------------
# Overview-siden kan fokusere på ét område eller ét anlæg. Valget skrives i URL'en (?po=3 eller ?site=12345),
# så det kan bogmærkes og deles. Funktionerne er rene (ingen Streamlit) og testes; kun anlaeg() er cachet.

NABO_KM = 20  # lus spredes mellem anlæg i samme fjordsystem; 20 km er den skala, naboerne vises på
MIN_NABOER = 5  # ligger færre inden for 20 km, fyldes op med de nærmeste


def anlaeg() -> pd.DataFrame:
    return _anlaeg(data_version())


@st.cache_data(max_entries=2)
def _anlaeg(version: float) -> pd.DataFrame:
    raa, panel, _ = _indlaes(version)
    return anlaeg_oversigt(raa, panel["uge_start"].max())


def anlaeg_oversigt(raa: pd.DataFrame, seneste: pd.Timestamp, uger: int = 52) -> pd.DataFrame:
    """Hvert anlæg, der har talt lus det seneste år: navn, område, position og seneste tælleuge (indeks: lokalitet)."""
    talt = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] > seneste - pd.Timedelta(weeks=uger)) & raa["omraade"].notna()]
    sidst = talt.sort_values("uge_start").drop_duplicates("lokalitet", keep="last").set_index("lokalitet")
    return sidst[["lokalitet_navn", "omraade", "lat", "lon", "uge_start"]].astype({"omraade": int}).rename(
        columns={"uge_start": "sidst_talt"}).sort_index()


def soegevalg(anlaeg: pd.DataFrame, navne: dict[int, str]) -> dict[str, str]:
    """Valgmuligheder til søgefeltet: nøgle ("po:3" / "site:12345") -> tekst.

    Først områderne, så anlæggene sorteret efter navn. Lokalitetsnummeret står i teksten, så anlæg med
    samme navn kan skelnes – og man kan søge på nummeret.
    """
    valg = {f"po:{o}": f"PO {o} · {n}" for o, n in sorted(navne.items())}
    lok = anlaeg.reset_index().sort_values(["lokalitet_navn", "lokalitet"],
                                            key=lambda s: s.str.lower() if s.name == "lokalitet_navn" else s)
    return valg | {f"site:{r.lokalitet}": f"{r.lokalitet_navn} · PO {r.omraade} · {r.lokalitet}" for r in lok.itertuples()}


def fra_url(params: dict, valg: dict[str, str]) -> str | None:
    """Søgenøglen fra URL'en (?site= vinder over ?po=). Ukendte eller ugyldige værdier giver None."""
    for navn in ("site", "po"):
        v = str(params.get(navn, "")).strip()
        if v.isdigit() and f"{navn}:{int(v)}" in valg:
            return f"{navn}:{int(v)}"
    return None


def til_url(noegle: str | None) -> dict[str, str]:
    """Søgenøglen som query-parametre: "site:12345" -> {"site": "12345"}; intet valg -> {}."""
    if not noegle:
        return {}
    navn, nr = noegle.split(":")
    return {navn: nr}


def afstand_km(lat: float, lon: float, lat2, lon2):
    """Storcirkelafstand (haversine) i km fra ét punkt til ét eller flere punkter."""
    f1, f2 = math.radians(lat), np.radians(lat2)
    a = np.sin((f2 - f1) / 2) ** 2 + math.cos(f1) * np.cos(f2) * np.sin(np.radians(np.asarray(lon2) - lon) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def graense_tal(s: pd.Series) -> pd.Series:
    """Lusegrænsen som tal ("0,5" / "0.2"); "Ukjent" og tomme felter bliver NaN."""
    return pd.to_numeric(s.astype(str).str.replace(",", "."), errors="coerce")


def naboer(anlaeg: pd.DataFrame, raa: pd.DataFrame, lokalitet: int, seneste: pd.Timestamp,
           km: float = NABO_KM, min_antal: int = MIN_NABOER) -> pd.DataFrame:
    """Anlæg tæt på det valgte, med seneste lusetal og udviklingen mod de 4 uger før – sorteret efter afstand.

    Alle inden for `km` tages med; er der færre end `min_antal`, fyldes op med de nærmeste.
    hunlus er seneste uge (NaN, hvis anlægget ikke talte); hunlus_4u_foer er snittet af de 4 uger før.
    """
    selv = anlaeg.loc[lokalitet]
    andre = anlaeg.drop(index=lokalitet).dropna(subset=["lat", "lon"])
    andre = andre.assign(km=afstand_km(float(selv["lat"]), float(selv["lon"]), andre["lat"], andre["lon"])).sort_values("km")
    andre = andre[(andre["km"] <= km) | (np.arange(len(andre)) < min_antal)]
    talt = raa[(raa["har_talt"] == "Ja") & raa["lokalitet"].isin(andre.index)
               & (raa["uge_start"] >= seneste - pd.Timedelta(weeks=4))]
    nu, foer = talt[talt["uge_start"] == seneste], talt[talt["uge_start"] < seneste]
    return andre.assign(
        hunlus=nu.groupby("lokalitet")["hunlus"].mean(),
        hunlus_4u_foer=foer.groupby("lokalitet")["hunlus"].mean(),
        over_graense=nu.groupby("lokalitet")["over_graense"].first(),
    ).rename_axis("lokalitet").reset_index()


def lokalitet_historik(raa: pd.DataFrame, lokalitet: int, naboer_: list[int], seneste: pd.Timestamp,
                       uger: int = 104) -> pd.DataFrame:
    """Anlæggets hunlus pr. uge, naboernes snit og områdets gældende lusegrænse på et komplet ugegitter.

    Uger uden tælling står som NaN. Grænsen tages fra områdets indberetninger, så den også står i uger,
    hvor anlægget ikke talte (0,2 i forårsugerne kommer på forskellige uger langs kysten).
    """
    fra = seneste - pd.Timedelta(weeks=uger - 1)
    r = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] >= fra) & (raa["uge_start"] <= seneste)]
    selv = r[r["lokalitet"] == lokalitet]
    omraade = selv["omraade"].dropna().iloc[-1] if len(selv) else None
    omr = r[r["omraade"] == omraade]
    gitter = pd.date_range(fra, seneste, freq="W-MON", name="uge_start")
    return pd.DataFrame({
        "hunlus": selv.groupby("uge_start")["hunlus"].mean(),
        "nabo_snit": r[r["lokalitet"].isin(naboer_)].groupby("uge_start")["hunlus"].mean(),
        "graense": graense_tal(omr["Lusegrense uke"]).groupby(omr["uge_start"]).median() if "Lusegrense uke" in omr else np.nan,
    }).reindex(gitter).reset_index()


# --- 8. Ugens udsving -----------------------------------------------------------------------

def udsving(raa: pd.DataFrame, seneste: pd.Timestamp, uger: int = 4) -> pd.DataFrame:
    """Hvert anlæg, der talte i seneste uge, med lusetal nu, snittet af de `uger` uger før og forskellen.

    Forskellen er i lus pr. fisk (ikke procent), så et fald fra 0,01 til 0 ikke ligner et dramatisk skift.
    Anlæg uden tælling i ugerne før har foer = NaN. Bruges til kortene "Worth a look this week".
    """
    talt = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] >= seneste - pd.Timedelta(weeks=uger))
               & (raa["uge_start"] <= seneste) & raa["omraade"].notna()]
    nu = talt[talt["uge_start"] == seneste].groupby("lokalitet").agg(
        lokalitet_navn=("lokalitet_navn", "first"), omraade=("omraade", "first"), nu=("hunlus", "mean"))
    foer = talt[talt["uge_start"] < seneste].groupby("lokalitet")["hunlus"].mean()
    return nu.assign(omraade=nu["omraade"].astype(int), foer=foer, forskel=lambda d: d["nu"] - d["foer"]).reset_index()
