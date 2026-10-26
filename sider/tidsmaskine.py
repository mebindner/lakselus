"""Tidsmaskine: 3D-kort med en søjle pr. lokalitet, afspillet uge for uge fra 2019 til nu."""

import streamlit as st
import streamlit.components.v1 as components

from lakselus import appdata, tidsmaskine

st.markdown("# Tidsmaskinen")
st.markdown(
    "Hver søjle er et havbrug. Jo højere og rødere, jo flere voksne hunlus pr. fisk. "
    "Tryk afspil og se lusene bølge op langs kysten hvert efterår – og falde igen, når vandet bliver koldt."
)


@st.cache_data(show_spinner="Pakker syv års lusetal …")
def side_html(skabelon_aendret: float) -> str:
    # Argumentet gør, at cachen fornyes, når HTML-skabelonen ændres.
    raa, _, _ = appdata.indlaes()
    return tidsmaskine.html(tidsmaskine.pak(raa))


components.html(side_html(tidsmaskine.SKABELON.stat().st_mtime), height=760)
st.caption(
    "Søjler vises kun i uger, hvor lokaliteten har talt lus (brakkede lokaliteter forsvinder). "
    "Kortet afspilles helt i din browser. Kystlinje fra Natural Earth (public domain)."
)
