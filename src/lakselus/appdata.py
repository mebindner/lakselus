"""Cachede dataopslag, som deles af siderne i Streamlit-appen."""

import ast

import pandas as pd
import streamlit as st

from lakselus import data, evaluering as ev
from lakselus.config import DATA_RAW

MODELLER = {"naiv": ev.naiv, "saeson_naiv": ev.saeson_naiv}
MODEL_NAVNE = {"naiv": "Naiv (sidste uge)", "saeson_naiv": "Sæson-naiv (samme uge sidste år)"}
TRAFIKLYS = {"green": "Grøn", "yellow": "Gul", "red": "Rød"}


@st.cache_data(show_spinner="Læser lusetal …")
def indlaes():
    raa = data.indlaes_raa()
    return raa, data.ugentligt_panel(raa), data.omraade_navne(raa)


@st.cache_data(show_spinner="Kører backtest …")
def kør_backtest(panel: pd.DataFrame) -> pd.DataFrame:
    res = {navn: ev.backtest(panel, f) for navn, f in MODELLER.items()}
    return ev.mae(res, efter=["omraade", "h"])


@st.cache_data
def omraader() -> pd.DataFrame:
    """Produktionsområder med omrids (lon/lat-polygon) og gældende trafiklysfarve."""
    po = pd.read_csv(DATA_RAW / "produktionsomraader.csv")
    po["polygon"] = po["geometry.coordinates"].map(lambda s: ast.literal_eval(s)[0])
    po["trafiklys"] = po["colors"].map(lambda s: ast.literal_eval(s)[-1]["color"])
    return po[["id", "name", "polygon", "trafiklys"]].rename(columns={"id": "omraade", "name": "navn"})


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
