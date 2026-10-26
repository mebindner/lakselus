"""Oversigt: kort over hele kysten og status pr. produktionsområde."""

import pandas as pd
import pydeck as pdk
import streamlit as st

from lakselus import appdata
from lakselus.udseende import HERO, LUS_FARVER, LYS_FARVER, ikon, kort, lus_niveau, trend


def rgba(hex_farve: str, alpha: int) -> list[int]:
    h = hex_farve.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [alpha]


def tal(v: float, d: int = 2) -> str:
    return f"{v:.{d}f}".replace(".", ",")


st.markdown(HERO, unsafe_allow_html=True)

raa, panel, navne = appdata.indlaes()
po = appdata.omraader()
status = appdata.status_pr_omraade(raa, panel)

seneste = panel["uge_start"].max()
iso = seneste.isocalendar()
talt = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] == seneste)]
aar_siden = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] == seneste - pd.Timedelta(weeks=52))]

# --- Nøgletal -----------------------------------------------------------------
st.markdown(f"### Uge {iso.week}, {iso.year} – hele kysten")
k1, k2, k3, k4 = st.columns(4)
k1.markdown(kort("Voksne hunlus pr. fisk", tal(talt["hunlus"].mean()),
                 f"samme uge sidste år: {tal(aar_siden['hunlus'].mean())}", "pest_control"), unsafe_allow_html=True)
k2.markdown(kort("Over lusegrænsen", f"{(talt['over_graense'] == 'Ja').mean():.0%}",
                 "af lokaliteterne denne uge", "warning"), unsafe_allow_html=True)
k3.markdown(kort("Lokaliteter med fisk", f"{len(talt):,}".replace(",", "."),
                 "har talt lus denne uge", "location_on"), unsafe_allow_html=True)
k4.markdown(kort("Havtemperatur", f"{tal(talt['temp'].mean(), 1)} °C",
                 "varmt vand = lus formerer sig hurtigere", "thermostat"), unsafe_allow_html=True)

# --- Kort ---------------------------------------------------------------------
st.markdown("### Kortet")
st.markdown(
    '<div class="forklaring">'
    f'<span><i class="prik" style="background:{LUS_FARVER["lav"]}"></i> under 0,2 hunlus</span>'
    f'<span><i class="prik" style="background:{LUS_FARVER["mellem"]}"></i> 0,2–0,5</span>'
    f'<span><i class="prik" style="background:{LUS_FARVER["hoej"]}"></i> over 0,5 (lusegrænsen)</span>'
    f'<span>{ikon("traffic", "#6B5F66")} områdets farve = myndighedernes trafiklys</span>'
    "</div>",
    unsafe_allow_html=True,
)

lokaliteter = talt.dropna(subset=["lat", "lon", "hunlus"]).copy()
lokaliteter["farve"] = lokaliteter["hunlus"].map(lambda v: rgba(LUS_FARVER[lus_niveau(v)], 220))
lokaliteter["tip"] = (
    "<b>" + lokaliteter["lokalitet_navn"] + "</b><br>" + lokaliteter["hunlus"].map(tal) + " voksne hunlus pr. fisk<br>"
    + lokaliteter["temp"].map(lambda t: tal(t, 1)) + " °C"
)
po_kort = po.assign(
    fyld=po["trafiklys"].map(lambda c: rgba(LYS_FARVER[c][0], 45)),
    kant=po["trafiklys"].map(lambda c: rgba(LYS_FARVER[c][0], 200)),
    tip="<b>" + po["omraade"].astype(str) + " · " + po["navn"] + "</b><br>Trafiklys: "
        + po["trafiklys"].map(appdata.TRAFIKLYS),
)

deck = pdk.Deck(
    layers=[
        pdk.Layer("PolygonLayer", po_kort, get_polygon="polygon", get_fill_color="fyld",
                  get_line_color="kant", line_width_min_pixels=1.2, pickable=True, auto_highlight=True),
        pdk.Layer("ScatterplotLayer", lokaliteter, get_position=["lon", "lat"], get_fill_color="farve",
                  get_radius=2600, radius_min_pixels=2.5, radius_max_pixels=9, stroked=True,
                  get_line_color=[255, 251, 245], line_width_min_pixels=0.6, pickable=True),
    ],
    initial_view_state=pdk.ViewState(latitude=66.3, longitude=16.5, zoom=3.9, pitch=0),
    # Scroll skal rulle siden, ikke zoome kortet; der zoomes med knapperne.
    views=[pdk.View(type="MapView", controller={"scrollZoom": False, "dragPan": True, "doubleClickZoom": True})],
    map_style=pdk.map_styles.CARTO_LIGHT,
    tooltip={"html": "{tip}", "style": {"backgroundColor": "#2E2633", "color": "#FFF8EE",
                                         "fontFamily": "Inter, sans-serif", "fontSize": "13px"}},
)
st.pydeck_chart(deck, height=620)
st.caption("Hver prik er en lokalitet, der har talt lus i seneste hele uge. Hold musen over for detaljer.")

# --- Områdekort ---------------------------------------------------------------
st.markdown("### Produktionsområderne – syd til nord")
st.markdown(
    '<div class="forklaring">'
    f'<span>{ikon("trending_up", "#C8473A")} stigende</span>'
    f'<span>{ikon("trending_flat", "#8C7F78")} stabil</span>'
    f'<span>{ikon("trending_down", "#2F6E8E")} faldende (mod snittet af de 4 uger før)</span>'
    f'<span>{ikon("warning", "#C8473A")} andel lokaliteter over grænsen</span>'
    "</div>",
    unsafe_allow_html=True,
)

bokse = []
for r in po.itertuples():
    s = status.loc[r.omraade] if r.omraade in status.index else None
    kant, bg, tekst = LYS_FARVER[r.trafiklys]
    if s is None:
        detaljer = '<div class="raekke"><span>Ingen tællinger denne uge</span></div>'
    else:
        t_ikon, t_farve, t_tekst = trend(s.hunlus, s.hunlus_4u_foer)
        advarsel = ("warning", "#C8473A") if s.andel_over >= 0.1 else (
            ("error", "#E3A72F") if s.andel_over > 0 else ("check_circle", "#5E9C6A"))
        detaljer = (
            '<div class="raekke">'
            f'<span title="{t_tekst}">{ikon("pest_control", LUS_FARVER[lus_niveau(s.hunlus)])}'
            f'<b>{tal(s.hunlus)}</b>&nbsp;{ikon(t_ikon, t_farve, t_tekst)}</span>'
            f'<span title="Andel lokaliteter over lusegrænsen">{ikon(*advarsel)} {s.andel_over:.0%}</span>'
            f'<span title="Havtemperatur">{ikon("thermostat", "#D9643A")} {tal(s.temp, 1)}°</span>'
            f'<span title="Lokaliteter der har talt">{ikon("location_on", "#6B5F66")} {int(s.n_lok)}</span>'
            "</div>"
        )
    bokse.append(
        f'<div class="omr" style="--lys:{kant};--lys-bg:{bg};--lys-tekst:{tekst}">'
        f'<div class="top"><span class="nr">{r.omraade}</span>'
        f'<span class="lys">{ikon("traffic")} {appdata.TRAFIKLYS[r.trafiklys]}</span></div>'
        f'<div class="navn">{r.navn}</div>{detaljer}</div>'
    )
st.markdown(f'<div class="omr-gitter">{"".join(bokse)}</div>', unsafe_allow_html=True)

st.write("")
with st.expander("Hvad er trafiklyset?"):
    st.markdown(
        "Norges 13 produktionsområder får hvert andet år en farve ud fra, hvor meget lakselus fra havbrug "
        "vurderes at påvirke den vilde laks. **Grøn** giver mulighed for at øge produktionen, **gul** fastholder "
        "den, og **rød** betyder, at den skal skæres ned. Farven her er den senest gældende fra BarentsWatch."
    )
