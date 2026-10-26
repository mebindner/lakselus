"""Tidsmaskine: 3D-kort med en søjle pr. lokalitet, afspillet uge for uge fra 2019 til nu."""

import streamlit as st

from lakselus import appdata, tidsmaskine
from lakselus.udseende import sidehoved

st.markdown(sidehoved(
    "Development · 2019 to today",
    "Sea lice week by week along the coast",
    "Each column is a fish farm site; height and colour show adult female lice per fish. Play the period and see "
    "how levels build up in late summer and fall again when the water cools.",
    [("view_in_ar", "3D – drag to rotate"), ("play_circle", "Play, pause and scrub")],
), unsafe_allow_html=True)


@st.cache_data(show_spinner="Packing seven years of lice counts …")
def side_html(skabelon_aendret: float) -> str:
    # Argumentet gør, at cachen fornyes, når HTML-skabelonen ændres.
    raa, _, _ = appdata.indlaes()
    return tidsmaskine.html(tidsmaskine.pak(raa))


st.iframe(side_html(tidsmaskine.SKABELON.stat().st_mtime), height=760)
st.caption(
    "Columns are shown only in weeks when the site counted lice (fallow sites disappear). "
    "The map plays entirely in your browser. Coastline from Natural Earth (public domain)."
)
