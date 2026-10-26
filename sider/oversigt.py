"""Oversigt: ugebrief i konsulentstil – executive summary, figurer med handlingstitler og metode."""

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
    return f"{v:.{d}f}".replace(".", ",")


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

retning = "lavere" if aendring < 0 else "højere"
st.markdown(sidehoved(
    f"Ugebrief · Lakselus i norsk havbrug · Uge {iso.week}, {iso.year}",
    f"Lusenivået er {abs(aendring):.0%} {retning} end for et år siden – presset er størst i {status.loc[top, 'navn']}",
    "Ugentlig status på lakselus i alle 13 produktionsområder, baseret på de lusetællinger, havbrugene indberetter "
    "til Mattilsynet. Tallene holdes op mod lusegrænsen, myndighedernes trafiklys og sæsonmønstret de seneste år.",
    [("verified", "Uafhængig analyse på åbne data"), ("database", "BarentsWatch / Mattilsynet"),
     ("location_on", f"{len(talt)} lokaliteter i ugens tal")],
), unsafe_allow_html=True)

st.markdown(resume([
    (tal(gns), f"voksne hunlus pr. fisk i snit langs kysten i uge {iso.week}. Det er {abs(aendring):.0%} "
               f"{retning} end i samme uge sidste år ({tal(gns_sidst)})."),
    (f"{len(over)} af {len(talt)}", f"lokaliteter ({pct(len(over) / len(talt))}) lå over lusegrænsen; flest i "
                                    + " og ".join(f"PO {o}" for o in over_pr_omr.index[:2]) + "."),
    (f"{len(roede)} af 13", "produktionsområder har rødt trafiklys og skal reducere produktionen: "
                            + ", ".join(roede["navn"]) + "."),
]), unsafe_allow_html=True)

# --- Figur 1: kort og rangering ------------------------------------------------------
st.markdown(figur(
    1, f"{status.loc[top, 'navn']} har det højeste lusetal blandt de store områder; {len(roede)} har rødt trafiklys",
    f"Voksne hunlus pr. fisk, uge {iso.week} {iso.year}. Kort: lokaliteter og produktionsområder farvet efter trafiklys.",
), unsafe_allow_html=True)

venstre, hoejre = st.columns([1, 1.15], gap="large")
with venstre:
    lok = talt.dropna(subset=["lat", "lon", "hunlus"]).copy()
    lok["farve"] = lok["hunlus"].map(lambda v: rgba(LUS_FARVER[lus_niveau(v)], 230))
    lok["tip"] = "<b>" + lok["lokalitet_navn"] + "</b><br>" + lok["hunlus"].map(tal) + " hunlus pr. fisk"
    po_kort = po.reset_index().assign(
        fyld=lambda d: d["trafiklys"].map(lambda c: rgba(LYS_FARVER[c][0], 30)),
        kant=lambda d: d["trafiklys"].map(lambda c: rgba(LYS_FARVER[c][0], 170)),
        tip=lambda d: "<b>PO " + d["omraade"].astype(str) + " · " + d["navn"] + "</b><br>Trafiklys: "
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
        x=alt.X("hunlus:Q", title="Voksne hunlus pr. fisk", scale=alt.Scale(domain=[0, 0.55]),
                axis=alt.Axis(format=".1f", tickCount=6, grid=True)),
        y=y,
        color=alt.Color("niveau:N", legend=None, scale=alt.Scale(
            domain=["lav", "mellem", "hoej"], range=[LUS_FARVER["lav"], LUS_FARVER["mellem"], LUS_FARVER["hoej"]])),
        tooltip=[alt.Tooltip("etiket:N", title="Område"), alt.Tooltip("hunlus:Q", title="Hunlus", format=".3f")],
    )
    tekster = alt.Chart(rang).mark_text(align="left", dx=4, fontSize=11, color="#1B2B36").encode(
        x="hunlus:Q", y=y, text="tekst:N")
    graenser = pd.DataFrame({"x": [0.2, 0.5], "t": ["0,2 forår", "0,5 lusegrænse"]})
    linjer = alt.Chart(graenser).mark_rule(strokeDash=[3, 3], color="#D64545", opacity=.7).encode(x="x:Q")
    linjetekst = alt.Chart(graenser).mark_text(align="left", dx=3, dy=-4, fontSize=10, color="#D64545").encode(
        x="x:Q", y=alt.value(0), text="t:N")
    st.altair_chart((soejler + tekster + linjer + linjetekst).properties(height=440), width="stretch")

st.markdown(
    '<div class="forklaring">'
    f'<span><i class="prik" style="background:{LUS_FARVER["lav"]}"></i>Under 0,2</span>'
    f'<span><i class="prik" style="background:{LUS_FARVER["mellem"]}"></i>0,2–0,5</span>'
    f'<span><i class="prik" style="background:{LUS_FARVER["hoej"]}"></i>Over 0,5</span>'
    f'<span><i class="prik" style="background:{LYS_FARVER["green"][0]}"></i><i class="prik" style="background:{LYS_FARVER["yellow"][0]}"></i>'
    f'<i class="prik" style="background:{LYS_FARVER["red"][0]}"></i>Trafiklys (områdefarve på kortet)</span></div>',
    unsafe_allow_html=True,
)
st.markdown(kilde(f"Områdetal er uvægtede gennemsnit over lokaliteter, der har talt lus i ugen. "
                  f"* Under {MIN_LOK} lokaliteter – tallet er usikkert og indgår ikke i konklusionerne."), unsafe_allow_html=True)

# --- Figur 2: statustabel -------------------------------------------------------------
st.markdown(figur(
    2, "Statusoversigt pr. produktionsområde",
    "Lusetal, udvikling mod de 4 foregående uger, andel lokaliteter over grænsen og havtemperatur.",
), unsafe_allow_html=True)

raekker = []
for o, s in status.iterrows():
    t_ikon, t_farve, t_tekst = trend(s.hunlus, s.hunlus_4u_foer)
    aend = s.hunlus / s.hunlus_4u_foer - 1 if s.hunlus_4u_foer else float("nan")
    farve = LUS_FARVER[lus_niveau(s.hunlus)]
    lys_kant, _, lys_tekst = LYS_FARVER[s.trafiklys]
    raekker.append(
        f'<tr><td class="po">{o}</td><td class="navn">{s.navn}{" <span style=\'color:#6B7A86\'>*</span>" if s.n_lok < MIN_LOK else ""}</td>'
        f'<td><i class="prik" style="background:{lys_kant}"></i>{appdata.TRAFIKLYS[s.trafiklys]}</td>'
        f'<td class="tal">{tal(s.hunlus)}<span class="minibar" style="width:{min(s.hunlus / 0.5, 1) * 60:.0f}px;background:{farve}"></span></td>'
        f'<td class="tal" style="color:{t_farve}">{ikon(t_ikon, t_farve, t_tekst)} {pct(aend, True) if pd.notna(aend) else "–"}</td>'
        f'<td class="tal" style="color:{"#D64545" if s.andel_over >= .1 else "inherit"}">{pct(s.andel_over)}</td>'
        f'<td class="tal">{tal(s.temp, 1)} °C</td><td class="tal">{int(s.n_lok)}</td></tr>'
    )
st.markdown(
    '<table class="tabel"><thead><tr><th>PO</th><th>Produktionsområde</th><th>Trafiklys</th>'
    '<th class="tal">Hunlus pr. fisk</th><th class="tal">Δ 4 uger</th><th class="tal">Over grænsen</th>'
    '<th class="tal">Havtemp.</th><th class="tal">Lokaliteter</th></tr></thead><tbody>'
    + "".join(raekker) + "</tbody></table>",
    unsafe_allow_html=True,
)
st.markdown(kilde(f"Δ 4 uger: ændring mod snittet af de fire foregående uger. * Under {MIN_LOK} lokaliteter."), unsafe_allow_html=True)

# --- Figur 3: små multipler ----------------------------------------------------------
foerste, i_aar = int(profil["foerste_aar"].iloc[0]), int(profil["aar"].iloc[0])
st.markdown(figur(
    3, f"{over_snit} af {len(uge_nu)} områder ligger over det normale niveau for årstiden",
    f"Voksne hunlus pr. fisk pr. uge. Linje: {i_aar}. Stiplet: snit {foerste}–{i_aar - 1}. Bånd: laveste–højeste niveau i samme periode.",
), unsafe_allow_html=True)

sm = profil.assign(titel=lambda d: "PO " + d["omraade"].astype(str) + " · " + d["omraade"].map(navne))
orden = [f"PO {o} · {navne[o]}" for o in sorted(navne)]
basis = alt.Chart().encode(x=alt.X("uge:Q", title=None, scale=alt.Scale(domain=[1, 52]),
                                   axis=alt.Axis(values=[1, 13, 26, 39, 52], grid=False, labelFontSize=9)))
baand = basis.mark_area(color=FARVER["taage"], opacity=.35).encode(
    y=alt.Y("lav:Q", title=None, axis=alt.Axis(values=[0, 0.5, 1], format=".1f", labelFontSize=9)), y2="hoej:Q")
snit = basis.mark_line(color=FARVER["skifer"], strokeDash=[3, 2], strokeWidth=1).encode(y="snit:Q")
nu = basis.mark_line(color=FARVER["laks"], strokeWidth=2).encode(y="i_aar:Q")
smaa = alt.layer(baand, snit, nu, data=sm).properties(width=225, height=90).facet(
    facet=alt.Facet("titel:N", sort=orden, header=alt.Header(labelFontSize=11, labelPadding=4)), columns=3,
).resolve_scale(y="shared")
st.altair_chart(smaa, width="content")
st.markdown(kilde(f"Uge 53 er udeladt. Snit og bånd bygger på {foerste}–{i_aar - 1}."), unsafe_allow_html=True)

# --- Figur 4: sæsonmønster -----------------------------------------------------------
st.markdown(figur(
    4, f"Toppen kommer senere, jo længere nordpå: omkring uge {syd_top} i syd mod uge {nord_top} i Finnmark",
    f"Gennemsnitligt antal voksne hunlus pr. fisk pr. ISO-uge, {foerste}–{i_aar - 1}.",
), unsafe_allow_html=True)
varme = alt.Chart(sm).mark_rect().encode(
    x=alt.X("uge:O", title="ISO-uge", axis=alt.Axis(values=[1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50], labelAngle=0)),
    y=alt.Y("titel:N", sort=orden, title=None, axis=alt.Axis(labelLimit=240, labelColor="#1B2B36", labelOverlap=False)),
    color=alt.Color("snit:Q", title="Hunlus pr. fisk", scale=alt.Scale(range=SEKVENS),
                    legend=alt.Legend(orient="right", gradientLength=180, format=".1f")),
    tooltip=[alt.Tooltip("titel:N", title="Område"), alt.Tooltip("uge:O", title="Uge"),
             alt.Tooltip("snit:Q", title="Snit", format=".3f")],
).properties(height=13 * 28)
st.altair_chart(varme, width="stretch")
st.markdown(kilde(), unsafe_allow_html=True)

# --- Metode ---------------------------------------------------------------------------
st.markdown(
    '<div class="metode"><b>Metode og forbehold.</b> Data er ugentlige lusetællinger pr. lokalitet fra BarentsWatch '
    "(indberettet til Mattilsynet). Områdetal er uvægtede gennemsnit over lokaliteter, der har talt lus i ugen; "
    "antal fisk pr. lokalitet indgår ikke. Den seneste uge medtages først, når mindst 80 % af lokaliteterne har "
    "indberettet. Lusegrænsen er 0,5 voksne hunlus pr. fisk (0,2 i forårsugerne). Trafiklyset er myndighedernes "
    "senest gældende farve pr. produktionsområde. Analysen er uafhængig og ikke udarbejdet for eller af nogen "
    "virksomhed.</div>",
    unsafe_allow_html=True,
)
