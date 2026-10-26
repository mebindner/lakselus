"""Streamlit-side. Start med:  streamlit run app.py"""

import altair as alt
import pandas as pd
import streamlit as st

from lakselus import KILDE_TEKST, data, evaluering as ev
from lakselus.config import har_noegle
from lakselus.udseende import CSS, FARVER, HERO, kort

st.set_page_config(page_title="Lakselus-forecast", page_icon="🐟", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(HERO, unsafe_allow_html=True)

MODELLER = {"naiv": ev.naiv, "saeson_naiv": ev.saeson_naiv}
MODEL_NAVNE = {"naiv": "Naiv (sidste uge)", "saeson_naiv": "Sæson-naiv (samme uge sidste år)"}


@st.cache_data(show_spinner="Læser lusetal …")
def indlaes():
    raa = data.indlaes_raa()
    return raa, data.ugentligt_panel(raa), data.omraade_navne(raa)


@st.cache_data(show_spinner="Kører backtest …")
def kør_backtest(panel: pd.DataFrame) -> pd.DataFrame:
    res = {navn: ev.backtest(panel, f) for navn, f in MODELLER.items()}
    return ev.mae(res, efter=["omraade", "h"])


try:
    raa, panel, navne = indlaes()
except FileNotFoundError:
    if har_noegle():
        st.info("Nøgle fundet, men ingen data endnu. Kør `python -m lakselus.hent`.")
    else:
        st.warning("Ingen API-nøgle fundet. Opret `.env` ud fra `.env.example` (se README).")
    st.stop()

# --- Nøgletal for seneste uge -------------------------------------------------
talt = raa[raa["har_talt"] == "Ja"]
seneste = talt["uge_start"].max()
denne_uge = talt[talt["uge_start"] == seneste]
aar_siden = talt[talt["uge_start"] == seneste - pd.Timedelta(weeks=52)]
iso = seneste.isocalendar()

st.markdown(f"### Uge {iso.week}, {iso.year} – hele kysten")
k1, k2, k3, k4 = st.columns(4)
gns, gns_sidst = denne_uge["hunlus"].mean(), aar_siden["hunlus"].mean()
k1.markdown(kort("Voksne hunlus pr. fisk", f"{gns:.2f}".replace(".", ","),
                 f"samme uge sidste år: {gns_sidst:.2f}".replace(".", ",")), unsafe_allow_html=True)
over = (denne_uge["over_graense"] == "Ja").mean()
k2.markdown(kort("Lokaliteter over lusegrænsen", f"{over:.0%}", "grænse 0,5 (0,2 i forårsugerne)"),
            unsafe_allow_html=True)
k3.markdown(kort("Lokaliteter der har talt", f"{len(denne_uge):,}".replace(",", "."), "med fisk i sjøen"),
            unsafe_allow_html=True)
k4.markdown(kort("Havtemperatur", f"{denne_uge['temp'].mean():.1f} °C".replace(".", ","), "gns. ved lokaliteterne"),
            unsafe_allow_html=True)

st.write("")

# --- Produktionsområde --------------------------------------------------------
st.markdown("### Vælg et produktionsområde")
valg = st.selectbox(
    "Produktionsområde", options=sorted(navne), format_func=lambda o: f"{o} · {navne[o]}",
    index=sorted(navne).index(3), label_visibility="collapsed",
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
st.markdown("### Hvor gode er prognoserne?")
st.markdown(
    "Backtest fra januar 2023: hver uge forudsiges 1–4 uger frem **kun med data, der fandtes på det tidspunkt**. "
    "Tallet er gennemsnitlig absolut fejl (MAE) i hunlus pr. fisk – lavere er bedre."
)
mae = kør_backtest(panel)
mae_omr = mae.xs(valg, level="omraade").rename(columns=MODEL_NAVNE)
mae_alle = mae.groupby(level="h").mean().rename(columns=MODEL_NAVNE)
tabel = pd.concat({f"Område {valg}": mae_omr, "Alle områder": mae_alle}, axis=1)
tabel.index = [f"{h} uge{'r' if h > 1 else ''} frem" for h in tabel.index]
st.dataframe(tabel.style.format("{:.3f}").highlight_min(axis=1, color="#F6D9B8"), width="stretch")
st.caption(
    "Den naive prognose er svær at slå: lusetallet ændrer sig langsomt fra uge til uge. "
    "En egentlig model tilføjes her, når den slår baselinen i backtesten."
)

st.markdown(
    f'<div class="fodnote">{KILDE_TEKST} Licens: NLOD. '
    f'<a href="https://www.barentswatch.no" target="_blank">barentswatch.no</a> · '
    f"Privat porteføljeprojekt · Data til og med uge {iso.week}, {iso.year}.</div>",
    unsafe_allow_html=True,
)
