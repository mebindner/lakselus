"""Cachede dataopslag, som deles af siderne i Streamlit-appen."""

import ast

import pandas as pd
import streamlit as st

from lakselus import data, evaluering as ev
from lakselus.config import DATA_RAW
from lakselus.data import APP_PRODUKTIONSOMRAADER

TRAFIKLYS = {"green": "Green", "yellow": "Yellow", "red": "Red"}


@st.cache_data(show_spinner="Loading lice counts …")
def indlaes():
    raa = data.indlaes_raa()
    return raa, data.ugentligt_panel(raa), data.omraade_navne(raa)


@st.cache_data
def omraader() -> pd.DataFrame:
    """Produktionsområder med omrids (lon/lat-polygon) og gældende trafiklysfarve."""
    fil = DATA_RAW / "produktionsomraader.csv"
    po = pd.read_csv(fil if fil.exists() else APP_PRODUKTIONSOMRAADER)
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


@st.cache_data(show_spinner="Running full backtest of all models (takes a few minutes the first time) …")
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


@st.cache_data(show_spinner=False)
def model_opsummering(res: pd.DataFrame) -> dict:
    from lakselus import modelrapport

    return modelrapport.opsummer(res)


@st.cache_data(show_spinner="Training the selected model on all data …")
def live_prognose(panel: pd.DataFrame, model: str, res: pd.DataFrame, niveau: float = 0.8) -> pd.DataFrame:
    """Prognose 1–4 uger frem fra seneste uge med den valgte model og et 80 %-interval pr. område.

    Intervallet er de empiriske kvantiler af modellens egne backtest-fejl for området og horisonten.
    """
    from lakselus import modeller

    f = (modeller.kandidater() | {"naiv": ev.naiv, "saeson_naiv": ev.saeson_naiv})[model]
    resid = res[res["model"] == model].assign(r=lambda d: d["faktisk"] - d["pred"])
    q = resid.groupby(["omraade", "h"])["r"].quantile([(1 - niveau) / 2, (1 + niveau) / 2]).unstack()
    q.columns = ["lo_r", "hi_r"]
    seneste = panel["uge_start"].max()
    rows = []
    for h in (1, 2, 3, 4):
        for omr, v in f(panel, h).items():
            lo, hi = q.loc[(omr, h)] if (omr, h) in q.index else (float("nan"), float("nan"))
            rows.append({"omraade": omr, "h": h, "uge_start": seneste + pd.Timedelta(weeks=h),
                         "pred": v, "lo": max(v + lo, 0), "hi": v + hi})
    return pd.DataFrame(rows)
