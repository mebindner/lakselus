"""Havstrømme: animeret kort over overfladestrømmen langs kysten i samme uge som lusetallene (engelsk UI).

Lakseluslarver driver med vandet, før de sætter sig på en fisk. Kortet viser, hvordan vandet i overfladen bevægede
sig – partiklerne er vand, ikke lus. Strømmen kommer fra MET Norways havmodel NorKyst v3 og hentes i den ugentlige
kørsel (python -m lakselus.havstroem); anlæggene farves efter ugens lusetal.

Indhold
1. Data         – strømfeltet og ugens lusetal pr. lokalitet
2. Sidehoved
3. Kortet       – partikelanimation i browseren (havstroem.html)
4. Metode og forbehold
"""

import pandas as pd
import streamlit as st

from lakselus import appdata, havstroem
from lakselus.udseende import sidehoved

# --- 1. Data --------------------------------------------------------------------------------
pakke = havstroem.indlaes()
raa, panel, _ = appdata.indlaes()
if pakke is None:
    st.info("No current data yet. Run `python -m lakselus.havstroem`.")
    st.stop()
uge_start = pd.Timestamp(pakke["uge_start"])
iso = uge_start.isocalendar()
anlaeg = havstroem.anlaeg_i_ugen(raa, uge_start)

# --- 2. Sidehoved ---------------------------------------------------------------------------
st.markdown(sidehoved(
    f"Currents · week {iso.week}, {iso.year}",
    "Sea lice larvae drift with the water – this is how the surface moved along the coast",
    "Lice larvae spend their first days drifting before they can attach to a fish, so the current decides where "
    "they end up. The particles show the daily mean surface current from MET Norway's ocean model; the dots are the "
    f"farms, coloured by their lice count in the same week. Week {iso.week} is the latest week with complete lice counts.",
    [("live", appdata.opdatering_tekst(panel)), ("waves", "Daily mean surface current, 7 days"),
     ("location_on", f"{len(anlaeg):,} farms that counted lice")],
), unsafe_allow_html=True)


# --- 3. Kortet ------------------------------------------------------------------------------
@st.cache_data(show_spinner="Unpacking a week of ocean currents …", max_entries=2)
def side_html(skabelon_aendret: float, stroem_aendret: float, data_version: float) -> str:
    # Argumenterne gør, at cachen fornyes, når skabelonen, strømmene eller lusetallene ændres.
    return havstroem.html(pakke, anlaeg)


st.iframe(side_html(havstroem.SKABELON.stat().st_mtime, havstroem.APP_FIL.stat().st_mtime, appdata.data_version()),
          height=720)

# --- 4. Metode og forbehold -------------------------------------------------------------------
st.markdown(
    '<div class="metode"><b>What the map shows.</b> Each particle follows the daily mean current in the top metre of '
    "the sea, from MET Norway's NorKyst v3 ocean model (800 m grid, shown here on a grid of about 3 km). The daily "
    "mean is taken over every third hour, which smooths out the tide and leaves the current that actually moves "
    "water along the coast over days. Brighter and longer streaks mean faster water. The animation is sped up "
    "many thousand times, so it shows direction and relative speed, not how fast a particle really travels."
    "<br><br><b>What it does not show.</b> The particles are water, not lice. Where larvae from a farm end up also "
    "depends on how many lice and fish the farm has, how long larvae survive at the sea temperature, and how they "
    "move up and down in the water. The Institute of Marine Research (Havforskningsinstituttet) models this in its "
    "official infection-pressure map, which the traffic-light system builds on. Narrow fjords and sounds are "
    "smoothed at 3 km, so currents close to many farms are only roughly shown."
    "<br><br><b>Source.</b> Surface currents: NorKyst v3, Norwegian Meteorological Institute (MET Norway), "
    "CC BY 4.0. Lice counts: BarentsWatch / Mattilsynet, NLOD. Coastline: Natural Earth.</div>",
    unsafe_allow_html=True,
)
