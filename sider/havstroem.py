"""Havstrømme: animeret kort over overfladestrømmen langs kysten i samme uge som lusetallene (engelsk UI).

Lakseluslarver driver med vandet, før de sætter sig på en fisk. Kortet viser, hvordan vandet i overfladen bevægede
sig – partiklerne er vand, ikke lus. Strømmen kommer fra MET Norways havmodel NorKyst v3 og hentes i den ugentlige
kørsel (python -m lakselus.havstroem); anlæggene farves efter ugens lusetal.

Indhold
1. Data         – strømfeltet, ugens lusetal pr. lokalitet og vandets fart ved anlæggene (km pr. døgn)
2. Sidehoved og resumé – konklusionen i ét tal, forskellen mellem områderne og hvor mange anlæg tallet bygger på
3. Kortet       – partikelanimation i browseren (havstroem.html)
4. Metode og forbehold
"""

import pandas as pd
import streamlit as st

from lakselus import appdata, havstroem
from lakselus.udseende import resume, sidehoved

# --- 1. Data --------------------------------------------------------------------------------
pakke = havstroem.indlaes()
raa, panel, navne = appdata.indlaes()
if pakke is None:
    st.info("No current data yet. Run `python -m lakselus.havstroem`.")
    st.stop()
uge_start = pd.Timestamp(pakke["uge_start"])
iso = uge_start.isocalendar()
anlaeg = havstroem.anlaeg_i_ugen(raa, uge_start)

# Hvor hurtigt flyttede vandet sig ved anlæggene? Et tal alle kan forholde sig til: km pr. døgn.
ugens = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] == uge_start)].dropna(subset=["lat", "lon", "omraade"])
fart = havstroem.fart_ved_anlaeg(pakke, ugens)
maalt = fart.dropna(subset=["km_dag"])
km_dag = maalt["km_dag"].median()
# Områder med færre end 10 målte anlæg bruges ikke i konklusionen (samme regel som på forsiden).
pr_omr = maalt.groupby(maalt["omraade"].astype(int))["km_dag"].agg(["median", "size"]).query("size >= 10")
hurtig, langsom = pr_omr["median"].idxmax(), pr_omr["median"].idxmin()
# Noterne på kortet: det hurtigste og det langsomste område, placeret midt i områdets anlæg.
def note(po: int, titel: str) -> list:
    a = maalt[maalt["omraade"].astype(int) == po]
    return [round(float(a["lon"].median()), 3), round(float(a["lat"].median()), 3), titel,
            f"{navne[po]}: {pr_omr.loc[po, 'median']:.0f} km a day"]


noter = [note(hurtig, "Fastest water near farms"), note(langsom, "Slowest water near farms")]

# --- 2. Sidehoved og resumé -------------------------------------------------------------------
st.markdown(sidehoved(
    f"Currents · week {iso.week}, {iso.year}",
    f"Near the farms, the surface water moved about {km_dag:.0f} km a day in week {iso.week} – "
    f"fastest in {navne[hurtig]}",
    "Sea lice larvae drift with the water for days before they can attach to a fish, so the current carries lice "
    "from one farm to its neighbours and to wild salmon. The map shows how the surface water moved, day by day, with "
    "every farm coloured by its lice count in the same week.",
    [("live", appdata.opdatering_tekst(panel)), ("waves", "Daily mean surface current, 7 days"),
     ("location_on", f"{len(anlaeg):,} farms that counted lice")],
), unsafe_allow_html=True)
INFO_KM = ("The daily mean surface current at the model cell nearest each farm, times one day; the median over farms "
           "and the seven days. The cell is often just outside the farm, in the open water in front of it, because the "
           "map's grid is about 3 km.")
st.markdown(resume([
    (f"{km_dag:.0f} km", f"a day: how far the surface water moved near a typical farm in week {iso.week}. "
                         "A larva drifting for several days can end up well beyond the neighbouring farm.", INFO_KM),
    (f"{pr_omr.loc[hurtig, 'median']:.0f} vs {pr_omr.loc[langsom, 'median']:.0f} km",
     f"a day in {navne[hurtig]} against {navne[langsom]} – the fastest and slowest of the "
     f"{len(pr_omr)} areas with at least 10 farms measured.",
     "Median over the area's farms. Areas with fewer than 10 farms are left out, as one farm can decide the figure."),
    (f"{len(maalt):,}", f"of the {len(fart):,} farms that counted lice are in the figures. The other "
                        f"{len(fart) - len(maalt)} lie deep in fjords narrower than the map's grid.",
     f"A farm counts if a model cell with water lies within {havstroem.MAKS_ANLAEG_KM:.0f} km."),
]), unsafe_allow_html=True)


# --- 3. Kortet ------------------------------------------------------------------------------
@st.cache_data(show_spinner="Unpacking a week of ocean currents …", max_entries=2)
def side_html(skabelon_aendret: float, stroem_aendret: float, data_version: float, noter_noegle: str) -> str:
    # Argumenterne gør, at cachen fornyes, når skabelonen, strømmene eller lusetallene ændres.
    return havstroem.html(pakke, anlaeg, noter)


st.iframe(side_html(havstroem.SKABELON.stat().st_mtime, havstroem.APP_FIL.stat().st_mtime, appdata.data_version(), str(noter)),
          height=720)

# --- 4. Metode og forbehold -------------------------------------------------------------------
st.markdown(
    '<div class="metode"><b>What the map shows.</b> Each particle follows the daily mean current at the sea surface '
    "(the model's top level), from MET Norway's NorKyst v3 ocean model (800 m grid, shown here on a grid of about 3 km). The daily "
    "mean is taken over every third hour, which smooths out the tide and leaves the current that actually moves "
    "water along the coast over days. Brighter and longer streaks mean faster water. The animation is sped up "
    "many thousand times, so it shows direction and relative speed, not how fast a particle really travels."
    "<br><br><b>What it does not show.</b> The particles are water, not lice. Where larvae from a farm end up also "
    "depends on how many lice and fish the farm has, how long larvae survive at the sea temperature, and how they "
    "move up and down in the water. The Institute of Marine Research (Havforskningsinstituttet) models this in its "
    "official infection-pressure map, which the traffic-light assessment draws on. Narrow fjords and sounds are "
    "smoothed at 3 km, so currents close to many farms are only roughly shown."
    "<br><br><b>Source.</b> Surface currents: NorKyst v3, Norwegian Meteorological Institute (MET Norway), "
    "CC BY 4.0. Lice counts: BarentsWatch / Mattilsynet, NLOD. Coastline: Natural Earth.</div>",
    unsafe_allow_html=True,
)
