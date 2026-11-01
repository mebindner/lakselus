"""Streamlit-app med tre sider (engelsk UI). Start med:  streamlit run app.py

Indhold
0. Friske moduler – genindlæs lakselus-pakken, hvis koden er ændret, mens appen kørte
1. Opsætning   – sidetitel, ordmærke i topbjælken og fælles designsystem (CSS)
2. Data        – indlæses én gang; uden data vises en vejledning i stedet for siderne
3. Navigation  – Overview, Time machine og Forecast i topbjælken
4. Fodnote     – afsender, opdateringsstatus og kildeangivelse (krav i BarentsWatch' vilkår)
"""

import importlib
import os
import sys
from pathlib import Path

import streamlit as st

# --- 0. Friske moduler ---------------------------------------------------------------------
# Streamlit Cloud henter ny kode ved et push uden altid at genstarte Python. Siderne køres så i ny version,
# mens lakselus-pakken stadig ligger i hukommelsen i den gamle – og en ny funktion "findes ikke".
# Den kompilerede .pyc-fil husker, hvilken version af kildefilen modulet blev indlæst fra; passer den ikke
# med filen på disken, genindlæses modulet. Efter en genindlæsning gemmes kildens tidsstempel på modulet,
# så kontrollen også holder, hvor Python ikke skriver .pyc-filer. Rækkefølgen følger afhængighederne,
# så et modul altid genindlæses efter dem, det importerer.
MODULER = ["config", "data", "udseende", "barentswatch", "evaluering", "modeller", "modelrapport",
           "behandlingseffekt", "tidsmaskine", "appdata"]


def _kilde_mtime(modul) -> int:
    return int(os.stat(modul.__file__).st_mtime) & 0xFFFFFFFF


def _er_foraeldet(modul) -> bool:
    try:
        indlaest = getattr(modul, "_indlaest_mtime", None)
        if indlaest is None:
            with open(modul.__cached__, "rb") as f:
                indlaest = int.from_bytes(f.read(12)[8:12], "little")  # pyc-header: magic, flag, kildens mtime
        return _kilde_mtime(modul) != indlaest
    except (OSError, TypeError, AttributeError):
        return False


def genindlaes_aendrede_moduler() -> None:
    aendret = False
    for navn in MODULER:
        modul = sys.modules.get(f"lakselus.{navn}")
        if modul is not None and (aendret or _er_foraeldet(modul)):
            importlib.reload(modul)
            modul._indlaest_mtime = _kilde_mtime(modul)
            aendret = True  # moduler efter et ændret modul kan have bundet dets gamle funktioner


genindlaes_aendrede_moduler()

from lakselus import KILDE_TEKST, appdata  # noqa: E402 – efter genindlæsningen
from lakselus.config import har_noegle  # noqa: E402
from lakselus.udseende import CSS  # noqa: E402

# --- 1. Opsætning ---------------------------------------------------------------------------
st.set_page_config(page_title="Sea lice in Norwegian salmon farming", page_icon="🐟", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.logo(str(Path(__file__).parent / "assets" / "logo.svg"), size="large")  # et klik fører til forsiden

# --- 2. Data -------------------------------------------------------------------------------
try:
    _, panel, _ = appdata.indlaes()
except FileNotFoundError:
    if har_noegle():
        st.info("API key found, but no data yet. Run `python -m lakselus.hent`.")
    else:
        st.warning("No API key found. Create `.env` from `.env.example` (see README).")
    st.stop()

# --- 3. Navigation -------------------------------------------------------------------------
side = st.navigation(
    [
        st.Page("sider/oversigt.py", title="Overview", icon=":material/map:", default=True),
        st.Page("sider/tidsmaskine.py", title="Time machine", icon=":material/view_in_ar:"),
        st.Page("sider/prognose.py", title="Forecast", icon=":material/insights:"),
    ],
    position="top",
)
side.run()

# --- 4. Fodnote ----------------------------------------------------------------------------
st.markdown(
    '<div class="fodnote"><div class="afsender">Built by '
    '<a href="https://www.linkedin.com/in/martin-eckberg-bindner-872207422" target="_blank">Martin Eckberg Bindner</a>'
    ' · Data analyst · <a href="https://github.com/mebindner/lakselus" target="_blank">Code on GitHub</a></div>'
    f'<div class="opdateret">{appdata.opdatering_tekst(panel)} · new lice counts every Wednesday</div>'
    f'{KILDE_TEKST} Licence: NLOD. '
    '<a href="https://www.barentswatch.no" target="_blank">barentswatch.no</a> · Independent portfolio project.</div>',
    unsafe_allow_html=True,
)
