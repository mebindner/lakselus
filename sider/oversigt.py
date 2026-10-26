"""Overview: ugebrief i konsulentstil – executive summary, figurer med handlingstitler og metode (engelsk UI)."""

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from lakselus import appdata
from lakselus.udseende import (
    FARVER, LUS_FARVER, LYS_FARVER, SEKVENS, figur, ikon, kilde, lus_niveau, resume, sidehoved, trend,
)


def rgba(hex_farve: str, alpha: int) -> list[int]:
    h = hex_farve.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [alpha]


def tal(v: float, d: int = 2) -> str:
    return f"{v:.{d}f}"


def pct(v: float, fortegn: bool = False) -> str:
    return (f"{v:+.0%}" if fortegn else f"{v:.0%}").replace("-", "−")


# --- Data og nøglefund ----------------------------------------------------------
raa, panel, navne = appdata.indlaes()
po = appdata.omraader().set_index("omraade")
status = appdata.status_pr_omraade(raa, panel).join(po[["navn", "trafiklys"]])
profil = appdata.saesonprofil(panel)

seneste = panel["uge_start"].max()
iso = seneste.isocalendar()
talt = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] == seneste)]
aar_siden = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] == seneste - pd.Timedelta(weeks=52))]

gns, gns_sidst = talt["hunlus"].mean(), aar_siden["hunlus"].mean()
aendring = gns / gns_sidst - 1
over = talt[talt["over_graense"] == "Ja"]
over_pr_omr = over.groupby("omraade").size().sort_values(ascending=False)
over_pr_omr.index = over_pr_omr.index.astype(int)
# Konklusioner bygger kun på områder med solidt datagrundlag; små områder vises, men markeres.
MIN_LOK = 10
solide = status[status["n_lok"] >= MIN_LOK]
top = solide["hunlus"].idxmax()
roede = po[po["trafiklys"] == "red"]
uge_nu = profil[profil["uge"] == iso.week].dropna(subset=["i_aar"])
over_snit = int((uge_nu["i_aar"] > uge_nu["snit"]).sum())
top_uge_pr_omr = profil.loc[profil.groupby("omraade")["snit"].idxmax()].set_index("omraade")["uge"]
syd_top, nord_top = int(top_uge_pr_omr.loc[[1, 2]].mean()), int(top_uge_pr_omr.loc[[12, 13]].mean())

retning = "lower" if aendring < 0 else "higher"
st.markdown(sidehoved(
    f"Weekly brief · Sea lice in Norwegian salmon farming · Week {iso.week}, {iso.year}",
    f"Lice levels are {abs(aendring):.0%} {retning} than a year ago – pressure is highest in {status.loc[top, 'navn']}",
    "Weekly status on sea lice (lakselus) in all 13 production areas (produksjonsområder), based on the lice counts "
    "fish farms report to the Norwegian Food Safety Authority. Figures are set against the lice limit (lusegrense), "
    "the government traffic-light system (trafikklyssystemet) and the seasonal pattern of recent years.",
    [("autorenew", "Updates automatically every Wednesday"), ("database", "BarentsWatch / Mattilsynet"),
     ("location_on", f"{len(talt)} sites in this week's figures"), ("verified", "Independent analysis of open data")],
), unsafe_allow_html=True)

st.markdown(resume([
    (tal(gns), f"adult female lice per fish on average along the coast in week {iso.week} – {abs(aendring):.0%} "
               f"{retning} than the same week last year ({tal(gns_sidst)})."),
    (f"{len(over)} of {len(talt)}", f"sites ({pct(len(over) / len(talt))}) were above the lice limit; most in "
                                    + " and ".join(f"PO {o}" for o in over_pr_omr.index[:2]) + "."),
    (f"{len(roede)} of 13", "production areas have a red traffic light and must reduce production: "
                            + ", ".join(roede["navn"]) + "."),
]), unsafe_allow_html=True)

# --- Figur 1: kort og rangering ------------------------------------------------------
st.markdown(figur(
    1, f"{status.loc[top, 'navn']} has the highest lice level among the larger areas; {len(roede)} have a red light",
    f"Adult female lice per fish, week {iso.week} {iso.year}. Map: sites and production areas coloured by traffic light.",
), unsafe_allow_html=True)

venstre, hoejre = st.columns([1, 1.15], gap="large")
with venstre:
    lok = talt.dropna(subset=["lat", "lon", "hunlus"]).copy()
    lok["farve"] = lok["hunlus"].map(lambda v: rgba(LUS_FARVER[lus_niveau(v)], 230))
    lok["tip"] = "<b>" + lok["lokalitet_navn"] + "</b><br>" + lok["hunlus"].map(tal) + " adult female lice per fish"
    po_kort = po.reset_index().assign(
        fyld=lambda d: d["trafiklys"].map(lambda c: rgba(LYS_FARVER[c][0], 30)),
        kant=lambda d: d["trafiklys"].map(lambda c: rgba(LYS_FARVER[c][0], 170)),
        tip=lambda d: "<b>PO " + d["omraade"].astype(str) + " · " + d["navn"] + "</b><br>Traffic light: "
                      + d["trafiklys"].map(appdata.TRAFIKLYS),
    )
    st.pydeck_chart(pdk.Deck(
        layers=[
            pdk.Layer("PolygonLayer", po_kort, get_polygon="polygon", get_fill_color="fyld",
                      get_line_color="kant", line_width_min_pixels=1, pickable=True, auto_highlight=True),
            pdk.Layer("ScatterplotLayer", lok, get_position=["lon", "lat"], get_fill_color="farve",
                      get_radius=2400, radius_min_pixels=2.2, radius_max_pixels=7, stroked=True,
                      get_line_color=[255, 255, 255], line_width_min_pixels=0.4, pickable=True),
        ],
        initial_view_state=pdk.ViewState(latitude=65.0, longitude=14.2, zoom=3.25),
        views=[pdk.View(type="MapView", controller={"scrollZoom": False, "dragPan": True, "doubleClickZoom": True})],
        map_style=pdk.map_styles.CARTO_LIGHT,
        tooltip={"html": "{tip}", "style": {"backgroundColor": "#0B2230", "color": "#FFFFFF",
                                             "fontFamily": "Inter, sans-serif", "fontSize": "12px"}},
    ), height=470)

with hoejre:
    rang = status.reset_index().assign(
        etiket=lambda d: "PO " + d["omraade"].astype(str) + "  " + d["navn"] + d["n_lok"].map(lambda n: " *" if n < MIN_LOK else ""),
        niveau=lambda d: d["hunlus"].map(lus_niveau),
        tekst=lambda d: d["hunlus"].map(tal),
    )
    rang = rang.sort_values("hunlus", ascending=False)
    y = alt.Y("etiket:N", sort=list(rang["etiket"]), title=None, axis=alt.Axis(labelLimit=220, labelFontSize=11.5, labelColor="#1B2B36"))
    soejler = alt.Chart(rang).mark_bar(height=15).encode(
        x=alt.X("hunlus:Q", title="Adult female lice per fish", scale=alt.Scale(domain=[0, 0.55]),
                axis=alt.Axis(format=".1f", tickCount=6, grid=True)),
        y=y,
        color=alt.Color("niveau:N", legend=None, scale=alt.Scale(
            domain=["lav", "mellem", "hoej"], range=[LUS_FARVER["lav"], LUS_FARVER["mellem"], LUS_FARVER["hoej"]])),
        tooltip=[alt.Tooltip("etiket:N", title="Area"), alt.Tooltip("hunlus:Q", title="Female lice", format=".3f")],
    )
    tekster = alt.Chart(rang).mark_text(align="left", dx=4, fontSize=11, color="#1B2B36").encode(
        x="hunlus:Q", y=y, text="tekst:N")
    # Grænseteksterne står på hver sin linje og vender ind mod midten, så de ikke overlapper på en smal skærm.
    graenser = pd.DataFrame({"x": [0.2, 0.5], "t": ["0.2 spring", "0.5 lice limit"]})
    linjer = alt.Chart(graenser).mark_rule(strokeDash=[3, 3], color="#D64545", opacity=.7).encode(x="x:Q")
    linjetekst = (
        alt.Chart(graenser.iloc[[0]]).mark_text(align="left", dx=3, fontSize=10, color="#D64545")
        .encode(x="x:Q", y=alt.value(-16), text="t:N")
        + alt.Chart(graenser.iloc[[1]]).mark_text(align="right", dx=-3, fontSize=10, color="#D64545")
        .encode(x="x:Q", y=alt.value(-4), text="t:N")
    )
    st.altair_chart((soejler + tekster + linjer + linjetekst).properties(height=440), width="stretch")

st.markdown(
    '<div class="forklaring">'
    f'<span><i class="prik" style="background:{LUS_FARVER["lav"]}"></i>Below 0.2</span>'
    f'<span><i class="prik" style="background:{LUS_FARVER["mellem"]}"></i>0.2–0.5</span>'
    f'<span><i class="prik" style="background:{LUS_FARVER["hoej"]}"></i>Above 0.5</span>'
    f'<span><i class="prik" style="background:{LYS_FARVER["green"][0]}"></i><i class="prik" style="background:{LYS_FARVER["yellow"][0]}"></i>'
    f'<i class="prik" style="background:{LYS_FARVER["red"][0]}"></i>Traffic light (area colour on the map)</span></div>',
    unsafe_allow_html=True,
)
st.markdown(kilde(f"Area figures are unweighted means over sites that counted lice that week. "
                  f"* Fewer than {MIN_LOK} sites – the figure is uncertain and excluded from the conclusions."), unsafe_allow_html=True)

# --- Figur 2: statustabel -------------------------------------------------------------
st.markdown(figur(
    2, "Status by production area",
    "Lice level, change vs. the previous 4 weeks, share of sites above the limit and sea temperature.",
), unsafe_allow_html=True)

raekker = []
for o, s in status.iterrows():
    t_ikon, t_farve, t_tekst = trend(s.hunlus, s.hunlus_4u_foer)
    aend = s.hunlus / s.hunlus_4u_foer - 1 if s.hunlus_4u_foer else float("nan")
    farve = LUS_FARVER[lus_niveau(s.hunlus)]
    lys_kant, _, lys_tekst = LYS_FARVER[s.trafiklys]
    raekker.append(
        f'<tr><td class="po">{o}</td><td class="navn">{s.navn}{" <span style=\'color:#6B7A86\'>*</span>" if s.n_lok < MIN_LOK else ""}</td>'
        f'<td><i class="prik" style="background:{lys_kant}"></i><span class="ekstra">{appdata.TRAFIKLYS[s.trafiklys]}</span></td>'
        f'<td class="tal">{tal(s.hunlus)}<span class="minibar" style="width:{min(s.hunlus / 0.5, 1) * 60:.0f}px;background:{farve}"></span></td>'
        f'<td class="tal" style="color:{t_farve}">{ikon(t_ikon, t_farve, t_tekst)} {pct(aend, True) if pd.notna(aend) else "–"}</td>'
        f'<td class="tal" style="color:{"#D64545" if s.andel_over >= .1 else "inherit"}">{pct(s.andel_over)}</td>'
        f'<td class="tal ekstra">{tal(s.temp, 1)} °C</td><td class="tal ekstra">{int(s.n_lok)}</td></tr>'
    )
st.markdown(
    '<table class="tabel"><thead><tr><th>PO</th><th>Production area</th><th>Traffic<span class="ekstra"> light</span></th>'
    '<th class="tal">Female lice / fish</th><th class="tal">Δ 4 weeks</th><th class="tal">Above limit</th>'
    '<th class="tal ekstra">Sea temp.</th><th class="tal ekstra">Sites</th></tr></thead><tbody>'
    + "".join(raekker) + "</tbody></table>",
    unsafe_allow_html=True,
)
st.markdown(kilde(f"Δ 4 weeks: change vs. the mean of the four preceding weeks. * Fewer than {MIN_LOK} sites."), unsafe_allow_html=True)

# --- Figur 3: små multipler ----------------------------------------------------------
foerste, i_aar = int(profil["foerste_aar"].iloc[0]), int(profil["aar"].iloc[0])
st.markdown(figur(
    3, f"{over_snit} of {len(uge_nu)} areas are above the normal level for the time of year",
    f"Adult female lice per fish per week. Line: {i_aar}. Dashed: mean {foerste}–{i_aar - 1}. Band: lowest–highest level in the same period.",
), unsafe_allow_html=True)

sm = profil.assign(titel=lambda d: "PO " + d["omraade"].astype(str) + " · " + d["omraade"].map(navne))
orden = [f"PO {o} · {navne[o]}" for o in sorted(navne)]
basis = alt.Chart().encode(x=alt.X("uge:Q", title=None, scale=alt.Scale(domain=[1, 52]),
                                   axis=alt.Axis(values=[1, 13, 26, 39, 52], grid=False, labelFontSize=9)))
baand = basis.mark_area(color=FARVER["taage"], opacity=.35).encode(
    y=alt.Y("lav:Q", title=None, axis=alt.Axis(values=[0, 0.5, 1], format=".1f", labelFontSize=9)), y2="hoej:Q")
snit = basis.mark_line(color=FARVER["skifer"], strokeDash=[3, 2], strokeWidth=1).encode(y="snit:Q")
nu = basis.mark_line(color=FARVER["laks"], strokeWidth=2).encode(y="i_aar:Q")
# Annotation: seneste uges værdi markeres og skrives direkte i hvert panel.
sm["er_sidste"] = sm["uge"] == sm.dropna(subset=["i_aar"])["uge"].max()
nu_pkt = basis.mark_circle(color=FARVER["laks"], size=26, opacity=1).encode(y="i_aar:Q").transform_filter("datum.er_sidste")
nu_tal = basis.mark_text(align="left", dx=5, fontSize=10, fontWeight=600, color=FARVER["laks"]).encode(
    y="i_aar:Q", text=alt.Text("i_aar:Q", format=".2f")).transform_filter("datum.er_sidste")
smaa = alt.layer(baand, snit, nu, nu_pkt, nu_tal, data=sm).properties(width=225, height=90).facet(
    facet=alt.Facet("titel:N", sort=orden, header=alt.Header(labelFontSize=11, labelPadding=4)), columns=3,
).resolve_scale(y="shared")
st.altair_chart(smaa, width="content")
st.markdown(kilde(f"Week 53 is omitted. Mean and band are based on {foerste}–{i_aar - 1}."), unsafe_allow_html=True)

# --- Figur 4: sæsonmønster -----------------------------------------------------------
st.markdown(figur(
    4, f"The peak comes later the further north: around week {syd_top} in the south vs. week {nord_top} in Finnmark",
    f"Mean adult female lice per fish by ISO week, {foerste}–{i_aar - 1}.",
), unsafe_allow_html=True)
vx = alt.X("uge:O", title="ISO week", axis=alt.Axis(values=[1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50], labelAngle=0))
vy = alt.Y("titel:N", sort=orden, title=None, axis=alt.Axis(labelLimit=240, labelColor="#1B2B36", labelOverlap=False))
varme = alt.Chart(sm).mark_rect().encode(
    x=vx, y=vy,
    color=alt.Color("snit:Q", title="Female lice / fish", scale=alt.Scale(range=SEKVENS),
                    legend=alt.Legend(orient="right", gradientLength=180, format=".1f")),
    tooltip=[alt.Tooltip("titel:N", title="Area"), alt.Tooltip("uge:O", title="Week"),
             alt.Tooltip("snit:Q", title="Mean", format=".3f")],
)
# Annotation: hvert områdes topuge markeres, så forskydningen mod nord kan ses direkte.
topper = sm.loc[sm.groupby("titel")["snit"].idxmax(), ["titel", "uge", "snit"]]
top_pkt = alt.Chart(topper).mark_point(shape="circle", filled=True, size=34, color="#FFFFFF", stroke=FARVER["blaek"],
                                       strokeWidth=1.2, opacity=1).encode(
    x=vx, y=vy, tooltip=[alt.Tooltip("titel:N", title="Area"), alt.Tooltip("uge:O", title="Peak week")])
st.altair_chart((varme + top_pkt).properties(height=13 * 28), width="stretch")
st.markdown(kilde("○ = the area's peak week (highest mean)."), unsafe_allow_html=True)

# --- Metode ---------------------------------------------------------------------------
st.markdown(
    '<div class="metode"><b>Method and caveats.</b> Data are weekly lice counts per site from BarentsWatch '
    "(reported to the Norwegian Food Safety Authority). Area figures are unweighted means over sites that counted "
    "lice that week; the number of fish per site is not included. The latest week is only included once at least "
    "80% of sites have reported. The lice limit is 0.5 adult female lice per fish (0.2 during the spring weeks). "
    "The traffic light is the government's most recent colour per production area. The analysis is independent "
    "and not prepared for or by any company.</div>",
    unsafe_allow_html=True,
)
