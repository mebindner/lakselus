"""History: er i år værre end normalt? Én kurve pr. år for lusetallet, og et fladt kort, der afspilles uge for uge.

Indhold
1. Data         – ugentligt gennemsnit for hele kysten eller ét område, pr. år og ISO-uge
2. Sidehoved    – konklusionen: i hvilke uger toppede lusetallet i de hele år, og hvor er i år?
3. Figur: år for år – tidligere år i gråt, i år fremhævet, bånd over de uger, toppen plejer at ligge i
4. Figur: kortet – hvert anlæg som en prik, afspillet uge for uge (tidsmaskine.html)
"""

import altair as alt
import pandas as pd
import streamlit as st

from lakselus import appdata, tidsmaskine
from lakselus.udseende import FARVER, figur, kilde, sidehoved

nr = iter(range(1, 5))  # figurnumre i rækkefølge

# --- 1. Data --------------------------------------------------------------------------------
raa, panel, navne = appdata.indlaes()
talt = raa[raa["har_talt"] == "Ja"]
KYST = 0
valg = st.selectbox("Whole coast or one production area", [KYST, *sorted(navne)], key="historik_omraade",
                    format_func=lambda o: "The whole coast" if o == KYST else f"PO {o} · {navne[o]}")
hvor = "along the coast" if valg == KYST else f"in {navne[valg]}"
# Kysten: gennemsnit over alle anlæg, der talte (som tidsmaskinens kurve). Et område: panelets områdetal.
serie = (talt.groupby("uge_start")["hunlus"].mean() if valg == KYST
         else panel[panel["omraade"] == valg].set_index("uge_start")["hunlus"]).dropna()
iso = serie.index.isocalendar()
aar = pd.DataFrame({"v": serie.to_numpy(), "aar": iso["year"].to_numpy(), "uge": iso["week"].to_numpy(),
                    "uge_start": serie.index})
aar = aar[aar["uge"] <= 52]  # uge 53 findes kun i nogle år
nu = int(aar["aar"].iloc[-1])
hele = aar[aar["aar"] < nu].groupby("aar").filter(lambda g: len(g) >= 50)
toppe = hele.loc[hele.groupby("aar")["v"].idxmax()]
i_aar = aar[aar["aar"] == nu]
top_nu = i_aar.loc[i_aar["v"].idxmax()]
sidste = toppe.iloc[-1]
seneste = i_aar.iloc[-1]
foerste = int(toppe["aar"].min())
# Ligger toppene tæt, er de ugers spænd konklusionen. Spreder de sig (fx i små nordlige områder), siger "uge 1–49"
# intet; så vises den typiske top (medianen) og båndet om den midterste halvdel af toppene.
smal = toppe["uge"].max() - toppe["uge"].min() <= 8
if smal:
    fra, til = int(toppe["uge"].min()), int(toppe["uge"].max())
else:
    fra, til = (int(round(q)) for q in toppe["uge"].quantile([0.25, 0.75]))
median_uge = int(round(toppe["uge"].median()))
# Områder med under 10 anlæg (samme regel som forsiden) får ingen konklusion: én enkelt tælling flytter kurven.
lille = valg != KYST and panel.loc[panel["omraade"] == valg, "n_lok"].tail(52).median() < 10

# --- 2. Sidehoved ---------------------------------------------------------------------------
st.markdown(sidehoved(
    f"History · {foerste} to today",
    (f"{navne[valg]} has fewer than 10 farms, so its yearly lice pattern is uncertain" if lille else
     f"Every year since {foerste}, lice {hvor} peaked between weeks {fra} and {til}" if smal else
     f"Lice {hvor} usually peak around week {median_uge}, but the timing varies a lot from year to year"),
    f"So far in {nu}, the average {hvor} has reached {top_nu['v']:.2f} adult female lice per fish (week "
    f"{int(top_nu['uge'])}), against a peak of {sidste['v']:.2f} in {int(sidste['aar'])}. Below: every year since "
    f"{foerste} on one chart, and a map that plays every farm week by week.",
    [("live", appdata.opdatering_tekst(panel)), ("calendar_month", f"{len(toppe)} complete years + {nu} so far"),
     ("play_circle", "Map: play, pause and scrub")],
), unsafe_allow_html=True)

# --- 3. Figur: år for år ----------------------------------------------------------------------
# Titlen siger det mest interessante, data viser: står i år højere end sidste års top, eller stiger det stadig,
# efter at toppen plejer at være passeret?
over_sidste = top_nu["v"] > sidste["v"]
stiger_sent = int(top_nu["uge"]) == int(seneste["uge"]) and int(seneste["uge"]) > til
if lille:
    f_titel = f"{nu} so far against every year since {foerste} – fewer than 10 farms, so the curves are noisy"
elif over_sidste:
    f_titel = f"{nu} is already above the {int(sidste['aar'])} peak ({top_nu['v']:.2f} in week {int(top_nu['uge'])})"
elif stiger_sent:
    f_titel = (f"{nu} is still rising in week {int(seneste['uge'])} ({seneste['v']:.2f}) – later than the "
               f"{'usual' if smal else 'typical'} peak in weeks {fra}–{til}, but below the {int(sidste['aar'])} peak of {sidste['v']:.2f}")
else:
    f_titel = (f"{nu} so far against every year since {foerste}: {seneste['v']:.2f} in week {int(seneste['uge'])}, "
               f"below the {int(sidste['aar'])} peak of {sidste['v']:.2f}")
st.markdown(figur(
    next(nr), f_titel,
    f"Adult female lice per fish {hvor}, by ISO week. Grey: {foerste}–{nu - 1}. Navy: {nu}. "
    + (f"Shaded: weeks {fra}–{til}, where the peak fell in every complete year." if smal else
       f"Shaded: weeks {fra}–{til}, where the middle half of the yearly peaks fell."),
), unsafe_allow_html=True)

x = alt.X("uge:Q", title="ISO week", scale=alt.Scale(domain=[1, 52], nice=False),
          axis=alt.Axis(values=[1, 10, 20, 30, 40, 52], grid=False))
y = alt.Y("v:Q", title="Adult female lice per fish")
tip = [alt.Tooltip("aar:O", title="Year"), alt.Tooltip("uge:Q", title="Week"),
       alt.Tooltip("v:Q", title="Female lice / fish", format=".2f")]
baand = alt.Chart(pd.DataFrame({"a": [fra], "b": [til]})).mark_rect(color=FARVER["model"], opacity=.12).encode(x="a:Q", x2="b:Q")
tidligere = alt.Chart(aar[aar["aar"] < nu]).mark_line(strokeWidth=1.1, color="#9AA7B1", opacity=.75).encode(
    x=x, y=y, detail="aar:O", tooltip=tip)
i_aar_linje = alt.Chart(i_aar).mark_line(strokeWidth=2.8, color=FARVER["blaek"]).encode(x=x, y=y, tooltip=tip)
punkt = alt.Chart(i_aar.tail(1)).mark_point(filled=True, size=60, color=FARVER["blaek"]).encode(x=x, y=y, tooltip=tip)
# Direkte etiketter i stedet for en forklaring: i år ved seneste punkt, sidste år ved sin top.
etiket_nu = alt.Chart(i_aar.tail(1).assign(t=f"{nu}: {seneste['v']:.2f}")).mark_text(
    align="right", dx=-6, dy=-12, fontSize=12, fontWeight=600, color=FARVER["blaek"]).encode(x=x, y=y, text="t:N")
etiket_sidst = alt.Chart(toppe.tail(1).assign(t=f"{int(sidste['aar'])} peak")).mark_text(
    align="left", dx=6, dy=-6, fontSize=11, color="#5B6B78").encode(x=x, y=y, text="t:N")
baand_tekst = alt.Chart(pd.DataFrame({"x": [fra], "t": ["usual peak" if smal else "typical peak"]})).mark_text(
    align="left", baseline="top", dx=4, dy=4, fontSize=10, color=FARVER["model"]).encode(
    x="x:Q", y=alt.value(0), text="t:N")
st.altair_chart((baand + tidligere + i_aar_linje + punkt + etiket_nu + etiket_sidst + baand_tekst).properties(height=340),
                width="stretch")
st.markdown(kilde(("Coast: mean over all farms that counted lice that week. " if valg == KYST else
                   "Area: unweighted mean over the area's farms that counted lice that week. ")
                  + f"Week 53 is left out. Years with fewer than 50 weeks of counts are not used for the peak weeks."),
            unsafe_allow_html=True)

# --- 4. Figur: kortet --------------------------------------------------------------------------
st.markdown(figur(
    next(nr), "Every farm, week by week – lice build up in late summer and fall again when the water cools",
    "Adult female lice per fish at each farm. The map plays the last 12 months and stops at the latest week; press play "
    "again to start from 2019. The curve under the map is the coast-wide average.",
), unsafe_allow_html=True)


@st.cache_data(show_spinner="Packing lice counts since 2019 …", max_entries=2)
def side_html(skabelon_aendret: float, data_version: float) -> str:
    # Argumenterne gør, at cachen fornyes, når HTML-skabelonen eller data ændres.
    raa, _, _ = appdata.indlaes()
    return tidsmaskine.html(tidsmaskine.pak(raa))


st.iframe(side_html(tidsmaskine.SKABELON.stat().st_mtime, appdata.data_version()), height=720)
st.markdown(kilde("Dots are shown only in weeks when the farm counted lice (fallow farms disappear). The map plays "
                  "entirely in your browser. Coastline: Natural Earth (public domain)."), unsafe_allow_html=True)
