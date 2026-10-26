"""Streamlit-app med tre sider (engelsk UI). Start med:  streamlit run app.py"""

import streamlit as st

from lakselus import KILDE_TEKST, appdata
from lakselus.config import har_noegle
from lakselus.udseende import CSS

st.set_page_config(page_title="Sea lice in Norwegian salmon farming", page_icon="🐟", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

try:
    appdata.indlaes()
except FileNotFoundError:
    if har_noegle():
        st.info("API key found, but no data yet. Run `python -m lakselus.hent`.")
    else:
        st.warning("No API key found. Create `.env` from `.env.example` (see README).")
    st.stop()

side = st.navigation(
    [
        st.Page("sider/oversigt.py", title="Overview", icon=":material/map:", default=True),
        st.Page("sider/tidsmaskine.py", title="Time machine", icon=":material/view_in_ar:"),
        st.Page("sider/prognose.py", title="Forecast", icon=":material/insights:"),
    ],
    position="top",
)
side.run()

st.markdown(
    '<div class="fodnote"><div class="afsender">Built by '
    '<a href="https://www.linkedin.com/in/martin-eckberg-bindner-872207422" target="_blank">Martin Eckberg Bindner</a>'
    ' · Data analyst · <a href="https://github.com/mebindner/lakselus" target="_blank">Code on GitHub</a></div>'
    f'{KILDE_TEKST} Licence: NLOD. '
    '<a href="https://www.barentswatch.no" target="_blank">barentswatch.no</a> · Independent portfolio project.</div>',
    unsafe_allow_html=True,
)
