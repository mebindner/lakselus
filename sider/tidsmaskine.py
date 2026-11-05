"""Tidsmaskine: 3D-kort med en søjle pr. lokalitet, afspillet uge for uge fra 2019 til nu."""

import pandas as pd
import streamlit as st

from lakselus import appdata, tidsmaskine
from lakselus.udseende import sidehoved

# Overskriften er en konklusion fra data: i hvilke uger toppede kystens gennemsnit i de hele år, og hvor er i år?
raa, panel, _ = appdata.indlaes()
talt = raa[raa["har_talt"] == "Ja"]
kyst = talt.groupby("uge_start")["hunlus"].mean()
iso = kyst.index.isocalendar()
aar = pd.DataFrame({"v": kyst.to_numpy(), "aar": iso["year"].to_numpy(), "uge": iso["week"].to_numpy()})
nu = int(aar["aar"].iloc[-1])
hele = aar[aar["aar"] < nu].groupby("aar").filter(lambda g: len(g) >= 52)
toppe = hele.loc[hele.groupby("aar")["v"].idxmax()]
i_aar = aar[aar["aar"] == nu].loc[lambda d: d["v"].idxmax()]
sidste = toppe.iloc[-1]

st.markdown(sidehoved(
    f"History · {int(toppe['aar'].min())} to today",
    f"Every year since {int(toppe['aar'].min())}, lice along the coast peaked between weeks {int(toppe['uge'].min())} "
    f"and {int(toppe['uge'].max())}",
    f"So far in {nu}, the coast-wide average has reached {i_aar['v']:.2f} adult female lice per fish (week "
    f"{int(i_aar['uge'])}), against a peak of {sidste['v']:.2f} in {int(sidste['aar'])}. Each column is a fish farm; "
    "height and colour show its lice count. The map plays the last 12 months – press play again to start from 2019.",
    [("live", appdata.opdatering_tekst(panel)), ("view_in_ar", "3D – rotate, tilt and zoom"),
     ("play_circle", "Play, pause and scrub")],
), unsafe_allow_html=True)


@st.cache_data(show_spinner="Packing lice counts since 2019 …", max_entries=2)
def side_html(skabelon_aendret: float, data_version: float) -> str:
    # Argumenterne gør, at cachen fornyes, når HTML-skabelonen eller data ændres.
    raa, _, _ = appdata.indlaes()
    return tidsmaskine.html(tidsmaskine.pak(raa))


st.iframe(side_html(tidsmaskine.SKABELON.stat().st_mtime, appdata.data_version()), height=760)
st.caption(
    "Columns are shown only in weeks when the farm counted lice (fallow farms disappear). "
    "The map plays entirely in your browser. Coastline from Natural Earth (public domain)."
)
