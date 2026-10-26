"""Prognose: historik, forecast 1–4 uger frem og ærlig backtest for ét produktionsområde."""

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from lakselus import appdata
from lakselus.appdata import MODEL_NAVNE, MODELLER
from lakselus.udseende import FARVER, figur, kilde, sidehoved

raa, panel, navne = appdata.indlaes()
seneste = panel["uge_start"].max()
iso = seneste.isocalendar()

st.markdown(sidehoved(
    "Prognose · 1–4 uger",
    "Prognose pr. produktionsområde",
    "Hvordan ser lusetallet ud de næste 1–4 uger – og hvor meget kan man stole på det? "
    "Alle prognoser er backtestet mod en naiv baseline.",
    [("calendar_month", f"Data til og med uge {iso.week}, {iso.year}"), ("history", "Backtest fra januar 2023")],
), unsafe_allow_html=True)

# --- Produktionsområde --------------------------------------------------------
valg = st.selectbox(
    "Produktionsområde", options=sorted(navne), format_func=lambda o: f"{o} · {navne[o]}",
    index=sorted(navne).index(3), key="omraade",
)
omr = panel[panel["omraade"] == valg].sort_values("uge_start")

# Handlingstitlen bygger på det højeste niveau, nogen af prognoserne når de næste fire uger.
maks = max(v for f in MODELLER.values() for h in (1, 2, 3, 4) if pd.notna(v := f(omr, h).get(valg)))
st.markdown(figur(
    1, f"{navne[valg]}: prognoserne for de næste fire uger ligger "
       f"{'under' if maks < 0.5 else 'over'} lusegrænsen (højst {maks:.2f})".replace(".", ","),
    "Voksne hunlus pr. fisk, sidste tre år og prognose 1–4 uger frem. Kort: lokaliteter i området i seneste uge.",
), unsafe_allow_html=True)
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
        line={"color": FARVER["hav"], "strokeWidth": 1.8},
        color=alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0, stops=[
            alt.GradientStop(color="#FFFFFF", offset=0), alt.GradientStop(color="#BFD3DF", offset=1)]),
        interpolate="monotone",
    ).encode(
        y=alt.Y("hunlus:Q", title="Voksne hunlus pr. fisk"),
        tooltip=[alt.Tooltip("uge_start:T", title="Uge", format="%d.%m.%Y"),
                 alt.Tooltip("hunlus:Q", title="Hunlus", format=".3f"),
                 alt.Tooltip("n_lok:Q", title="Lokaliteter")],
    )
    graense = alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(
        color="#D64545", strokeDash=[4, 4], strokeWidth=1.2).encode(y="y:Q")
    graense_tekst = alt.Chart(pd.DataFrame({"y": [0.5], "t": ["lusegrænse 0,5"]})).mark_text(
        align="left", dx=4, dy=-7, color="#D64545", fontSize=11, font="Inter").encode(
        y="y:Q", text="t:N", x=alt.value(0))
    punkter = alt.Chart(prognose).mark_line(point=alt.OverlayMarkDef(size=60, filled=True), strokeWidth=2).encode(
        x="uge_start:T", y="hunlus:Q",
        color=alt.Color("model:N", title="Prognose",
                        scale=alt.Scale(range=[FARVER["laks"], FARVER["skifer"]]),
                        legend=alt.Legend(orient="bottom", titleOrient="left", labelLimit=0)),
        tooltip=["model:N", alt.Tooltip("h:Q", title="Uger frem"), alt.Tooltip("hunlus:Q", format=".3f")],
    )
    graf = (flade + graense + graense_tekst + punkter).properties(height=360).configure_view(stroke=None).configure_axis(
        grid=True, gridColor="#E6ECF0", domain=False, labelColor="#55687A", titleColor="#55687A", labelFont="Inter", titleFont="Inter").configure_legend(labelFont="Inter", titleFont="Inter", labelColor="#1B2B36")
    st.altair_chart(graf, width="stretch")

with hoejre:
    seneste_omr = raa[(raa["omraade"] == valg) & (raa["uge_start"] == seneste)].dropna(subset=["lat", "lon"])
    farver = {"Ja": [214, 69, 69, 230], "Nei": [31, 122, 140, 230]}
    seneste_omr = seneste_omr.assign(
        farve=seneste_omr["over_graense"].map(lambda v: farver.get(v, [184, 195, 204, 200])),
        navn=seneste_omr["lokalitet_navn"])
    st.pydeck_chart(pdk.Deck(
        layers=[pdk.Layer("ScatterplotLayer", seneste_omr, get_position=["lon", "lat"], get_fill_color="farve",
                          get_radius=1500, radius_min_pixels=3, radius_max_pixels=8, stroked=True,
                          get_line_color=[255, 255, 255], line_width_min_pixels=0.5, pickable=True)],
        initial_view_state=pdk.ViewState(latitude=seneste_omr["lat"].mean(), longitude=seneste_omr["lon"].mean(), zoom=6.2),
        views=[pdk.View(type="MapView", controller={"scrollZoom": False, "dragPan": True})],
        map_style=pdk.map_styles.CARTO_LIGHT,
        tooltip={"text": "{navn}"},
    ), height=360)
    st.caption("Lokaliteter i området i seneste uge. Rød = over lusegrænsen, blå = under, grå = ingen tælling.")

# --- Ærlig evaluering ---------------------------------------------------------
st.markdown(kilde("Områdetal er uvægtede gennemsnit over lokaliteter, der har talt lus i ugen."), unsafe_allow_html=True)

st.markdown(figur(
    2, "Den naive prognose er svær at slå – en model skal bevise sin værdi i backtesten",
    "Gennemsnitlig absolut fejl (MAE) i hunlus pr. fisk, backtest fra januar 2023. Hver uge forudsiges 1–4 uger frem "
    "kun med data, der fandtes på det tidspunkt. Laveste fejl pr. række er fremhævet.",
), unsafe_allow_html=True)
mae = appdata.kør_backtest(panel)
mae_omr = mae.xs(valg, level="omraade").rename(columns=MODEL_NAVNE)
mae_alle = mae.groupby(level="h").mean().rename(columns=MODEL_NAVNE)
tabel = pd.concat({f"Område {valg}": mae_omr, "Alle områder": mae_alle}, axis=1)
tabel.index = [f"{h} uge{'r' if h > 1 else ''} frem" for h in tabel.index]
st.dataframe(tabel.style.format("{:.3f}").highlight_min(axis=1, color="#FDE3DC"), width="stretch")
st.markdown(kilde("Lusetallet ændrer sig langsomt fra uge til uge, så sidste uges niveau er en stærk baseline. "
                  "En egentlig model tilføjes, når den slår baselinen."), unsafe_allow_html=True)
