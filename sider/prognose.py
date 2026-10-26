"""Prognose: historik, forecast 1–4 uger frem og ærlig backtest for ét produktionsområde."""

import altair as alt
import pandas as pd
import streamlit as st

from lakselus import appdata
from lakselus.appdata import MODEL_NAVNE, MODELLER
from lakselus.udseende import FARVER

st.markdown("# Prognose pr. produktionsområde")
st.markdown("Hvordan ser lusetallet ud de næste 1–4 uger – og hvor meget kan man stole på det?")

raa, panel, navne = appdata.indlaes()
seneste = panel["uge_start"].max()
iso = seneste.isocalendar()

# --- Produktionsområde --------------------------------------------------------
valg = st.selectbox(
    "Produktionsområde", options=sorted(navne), format_func=lambda o: f"{o} · {navne[o]}",
    index=sorted(navne).index(3), key="omraade",
)
omr = panel[panel["omraade"] == valg].sort_values("uge_start")

venstre, hoejre = st.columns([2.2, 1])

with venstre:
    historik = omr[omr["uge_start"] >= seneste - pd.Timedelta(weeks=156)]
    prognose = pd.DataFrame([
        {"uge_start": seneste + pd.Timedelta(weeks=h), "h": h, "model": MODEL_NAVNE[navn],
         "hunlus": f(omr, h).get(valg)}
        for navn, f in MODELLER.items() for h in (1, 2, 3, 4)
    ]).dropna()

    basis = alt.Chart(historik).encode(x=alt.X("uge_start:T", title=None, axis=alt.Axis(format="%b %Y")))
    flade = basis.mark_area(
        line={"color": FARVER["laks"], "strokeWidth": 2},
        color=alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0, stops=[
            alt.GradientStop(color="#FBF4EA", offset=0), alt.GradientStop(color="#F2B08A", offset=1)]),
        interpolate="monotone",
    ).encode(
        y=alt.Y("hunlus:Q", title="Voksne hunlus pr. fisk"),
        tooltip=[alt.Tooltip("uge_start:T", title="Uge", format="%d.%m.%Y"),
                 alt.Tooltip("hunlus:Q", title="Hunlus", format=".3f"),
                 alt.Tooltip("n_lok:Q", title="Lokaliteter")],
    )
    graense = alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(
        color=FARVER["lyng"], strokeDash=[5, 4]).encode(y="y:Q")
    graense_tekst = alt.Chart(pd.DataFrame({"y": [0.5], "t": ["lusegrænse 0,5"]})).mark_text(
        align="left", dx=4, dy=-7, color=FARVER["lyng"], fontSize=11).encode(
        y="y:Q", text="t:N", x=alt.value(0))
    punkter = alt.Chart(prognose).mark_line(point=alt.OverlayMarkDef(size=60, filled=True), strokeWidth=2).encode(
        x="uge_start:T", y="hunlus:Q",
        color=alt.Color("model:N", title="Prognose",
                        scale=alt.Scale(range=[FARVER["fjord"], FARVER["rav"]]),
                        legend=alt.Legend(orient="bottom", titleOrient="left", labelLimit=0)),
        tooltip=["model:N", alt.Tooltip("h:Q", title="Uger frem"), alt.Tooltip("hunlus:Q", format=".3f")],
    )
    graf = (flade + graense + graense_tekst + punkter).properties(height=360).configure_view(stroke=None).configure_axis(
        grid=True, gridColor="#EBDCC8", domain=False, labelColor="#6B5F66", titleColor="#6B5F66")
    st.altair_chart(graf, width="stretch")
    st.caption("Sidste tre år og prognose 1–4 uger frem. Område-tallet er et uvægtet gennemsnit over lokaliteter, der har talt.")

with hoejre:
    seneste_omr = raa[(raa["omraade"] == valg) & (raa["uge_start"] == seneste)].dropna(subset=["lat", "lon"])
    seneste_omr = seneste_omr.assign(
        farve=seneste_omr["over_graense"].map({"Ja": "#D9643A", "Nei": "#2F4B6E"}).fillna("#B8ABA0"))
    st.map(seneste_omr, latitude="lat", longitude="lon", color="farve", size=900, height=330)
    st.caption("Lokaliteter i området i seneste uge. Orange = over lusegrænsen, blå = under, grå = ingen tælling.")

# --- Ærlig evaluering ---------------------------------------------------------
st.markdown(f"### Hvor gode er prognoserne? <small style='font-size:.6em;color:#8C7F78'>data til og med uge {iso.week}, {iso.year}</small>", unsafe_allow_html=True)
st.markdown(
    "Backtest fra januar 2023: hver uge forudsiges 1–4 uger frem **kun med data, der fandtes på det tidspunkt**. "
    "Tallet er gennemsnitlig absolut fejl (MAE) i hunlus pr. fisk – lavere er bedre."
)
mae = appdata.kør_backtest(panel)
mae_omr = mae.xs(valg, level="omraade").rename(columns=MODEL_NAVNE)
mae_alle = mae.groupby(level="h").mean().rename(columns=MODEL_NAVNE)
tabel = pd.concat({f"Område {valg}": mae_omr, "Alle områder": mae_alle}, axis=1)
tabel.index = [f"{h} uge{'r' if h > 1 else ''} frem" for h in tabel.index]
st.dataframe(tabel.style.format("{:.3f}").highlight_min(axis=1, color="#F6D9B8"), width="stretch")
st.caption(
    "Den naive prognose er svær at slå: lusetallet ændrer sig langsomt fra uge til uge. "
    "En egentlig model tilføjes her, når den slår baselinen i backtesten."
)
