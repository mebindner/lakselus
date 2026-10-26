"""Tidsmaskine: 3D-kort med en søjle pr. lokalitet, afspillet uge for uge fra 2019 til nu."""

import streamlit as st

from lakselus import appdata, tidsmaskine
from lakselus.udseende import sidehoved

st.markdown(sidehoved(
    "Udvikling · 2019 til i dag",
    "Lusetal uge for uge langs kysten",
    "Hver søjle er en lokalitet; højde og farve viser voksne hunlus pr. fisk. Afspil perioden og se, hvordan "
    "niveauet bygger sig op i sensommeren og falder igen, når vandet bliver koldt.",
    [("view_in_ar", "3D – træk for at dreje"), ("play_circle", "Afspil, pause og spol")],
), unsafe_allow_html=True)


@st.cache_data(show_spinner="Pakker syv års lusetal …")
def side_html(skabelon_aendret: float) -> str:
    # Argumentet gør, at cachen fornyes, når HTML-skabelonen ændres.
    raa, _, _ = appdata.indlaes()
    return tidsmaskine.html(tidsmaskine.pak(raa))


st.iframe(side_html(tidsmaskine.SKABELON.stat().st_mtime), height=760)
st.caption(
    "Søjler vises kun i uger, hvor lokaliteten har talt lus (brakkede lokaliteter forsvinder). "
    "Kortet afspilles helt i din browser. Kystlinje fra Natural Earth (public domain)."
)
