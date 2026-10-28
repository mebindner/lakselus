"""Tidsmaskine: 3D-kort med en søjle pr. lokalitet, afspillet uge for uge fra 2019 til nu."""

import streamlit as st

from lakselus import appdata, tidsmaskine
from lakselus.udseende import sidehoved

st.markdown(sidehoved(
    "Development · 2019 to today",
    "Sea lice week by week along the coast",
    "Each column is a fish farm site; height and colour show adult female lice per fish. Play the period and see "
    "how levels build up in late summer and fall again when the water cools.",
    [("live", appdata.opdatering_tekst(appdata.indlaes()[1])), ("view_in_ar", "3D – rotate, tilt and zoom"),
     ("play_circle", "Play, pause and scrub")],
), unsafe_allow_html=True)


@st.cache_data(show_spinner="Packing seven years of lice counts …", max_entries=2)
def side_html(skabelon_aendret: float, data_version: float) -> str:
    # Argumenterne gør, at cachen fornyes, når HTML-skabelonen eller data ændres.
    raa, _, _ = appdata.indlaes()
    return tidsmaskine.html(tidsmaskine.pak(raa))


st.iframe(side_html(tidsmaskine.SKABELON.stat().st_mtime, appdata.data_version()), height=760)
st.caption(
    "Columns are shown only in weeks when the site counted lice (fallow sites disappear). "
    "The map plays entirely in your browser. Coastline from Natural Earth (public domain)."
)
