"""Streamlit-app med to sider. Start med:  streamlit run app.py"""

import streamlit as st

from lakselus import KILDE_TEKST, appdata
from lakselus.config import har_noegle
from lakselus.udseende import CSS

st.set_page_config(page_title="Lakselus langs norskekysten", page_icon="🐟", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

try:
    appdata.indlaes()
except FileNotFoundError:
    if har_noegle():
        st.info("Nøgle fundet, men ingen data endnu. Kør `python -m lakselus.hent`.")
    else:
        st.warning("Ingen API-nøgle fundet. Opret `.env` ud fra `.env.example` (se README).")
    st.stop()

side = st.navigation(
    [
        st.Page("sider/oversigt.py", title="Oversigt", icon=":material/map:", default=True),
        st.Page("sider/tidsmaskine.py", title="Tidsmaskine", icon=":material/view_in_ar:"),
        st.Page("sider/prognose.py", title="Prognose", icon=":material/insights:"),
    ],
    position="top",
)
side.run()

st.markdown(
    f'<div class="fodnote">{KILDE_TEKST} Licens: NLOD. '
    '<a href="https://www.barentswatch.no" target="_blank">barentswatch.no</a> · Privat porteføljeprojekt.</div>',
    unsafe_allow_html=True,
)
