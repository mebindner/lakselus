"""Streamlit-app med tre sider (engelsk UI). Start med:  streamlit run app.py

Indhold
0. Friske moduler – genindlæs lakselus-pakken, hvis koden er ændret, mens appen kørte
1. Opsætning   – sidetitel, ordmærke i topbjælken og fælles designsystem (CSS)
2. Data        – indlæses én gang; uden data vises en vejledning i stedet for siderne
3. Navigation  – Latest week, History og Forecast i topbjælken
4. Fodnote     – About (hvem, data, metode, kode), opdateringsstatus og kildeangivelse (krav i BarentsWatch' vilkår)
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
# Fanen i browseren bruger samme mærke som ordmærket; titlen sættes pr. side under navigationen.
st.set_page_config(page_title="Sea lice Norway", page_icon=str(Path(__file__).parent / "assets" / "favicon.png"),
                   layout="wide")
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
        # Navnene siger, hvad man får: den seneste færdigindberettede uge, udviklingen siden 2019 og prognosen
        st.Page("sider/oversigt.py", title="Latest week", icon=":material/map:", default=True),
        st.Page("sider/tidsmaskine.py", title="History", icon=":material/view_in_ar:"),
        st.Page("sider/prognose.py", title="Forecast", icon=":material/insights:"),
    ],
    position="top",
)
st.set_page_config(page_title=f"{side.title} · Sea lice Norway")  # fx "Forecast · Sea lice Norway" i fanen
side.run()

# --- 4. Fodnote ----------------------------------------------------------------------------
# About samler det, en besøgende (fx fra LinkedIn) vil vide: hvem står bag, hvor data kommer fra, metoden og koden.
st.markdown(
    '<div class="om" id="about"><div class="om-hoved">About this project</div><div class="om-gitter">'
    '<div><b>Who</b>An independent spare-time project by '
    '<a href="https://www.linkedin.com/in/martin-eckberg-bindner-872207422" target="_blank">Martin Eckberg Bindner</a>, '
    'data analyst. It turns the open weekly lice reports from Norwegian fish farms into a brief anyone can read. '
    'Not prepared for or by any company.</div>'
    '<div><b>Data</b>Weekly lice counts, sea temperature and treatments for every site, reported to the Norwegian '
    'Food Safety Authority (Mattilsynet) and published by BarentsWatch under the NLOD licence. New counts arrive '
    'every Wednesday; the pages show the latest week that is fully reported.</div>'
    '<div><b>Method</b>Area figures are plain means over the sites that counted, not weighted by fish. Forecasts are '
    'tested week by week on seasons the models never saw. Every page ends with its own notes on method and caveats.</div>'
    '<div><b>Code</b>Python, pandas, scikit-learn, Streamlit, Altair and deck.gl, open source on '
    '<a href="https://github.com/mebindner/lakselus" target="_blank">GitHub</a>. Developed with AI-assisted coding '
    '(Claude); problem framing, methodology, model validation and design decisions are my own.</div>'
    '</div></div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="fodnote"><div class="opdateret">{appdata.opdatering_tekst(panel)} · new lice counts every Wednesday</div>'
    f'{KILDE_TEKST} Licence: NLOD. '
    '<a href="https://www.barentswatch.no" target="_blank">barentswatch.no</a> · Independent portfolio project.</div>',
    unsafe_allow_html=True,
)
