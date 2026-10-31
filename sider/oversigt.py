"""Overview: ugebrief i konsulentstil – executive summary, figurer med handlingstitler og metode (engelsk UI).

Indhold
0. Hjælpefunktioner
1. Data og nøglefund       – seneste uge, lusegrænse, trafiklys og indberetningsstatus
2. Sidehoved og resumé     – overskrift og tre nøgletal
3. Figur 1: kort + søjler  – klik på et område viser hvert anlæg i området
4. Figur 2: statustabel
5. Figur 3: små multipler  – i år mod tidligere år pr. område
6. Figur 4: sæsonmønster
7. Metode og forbehold
"""

import math

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from lakselus import appdata
from lakselus.udseende import (
    FARVER, LAVT_NIVEAU, LUS_FARVER, LYS_FARVER, SEKVENS, figur, ikon, kilde, lus_niveau, resume, sidehoved, trend,
)


# --- 0. Hjælpefunktioner ---------------------------------------------------------------

def rgba(hex_farve: str, alpha: int) -> list[int]:
    h = hex_farve.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [alpha]


def tal(v: float, d: int = 2) -> str:
    return f"{v:.{d}f}"


def pct(v: float, fortegn: bool = False) -> str:
    return (f"{v:+.0%}" if fortegn else f"{v:.0%}").replace("-", "−")


# --- 1. Data og nøglefund -------------------------------------------------------
raa, panel, navne = appdata.indlaes()
seneste = panel["uge_start"].max()
# Trafiklyset slås op for den viste uge – det er en politisk beslutning hvert andet år, ikke ugens lusetal.
po = appdata.trafiklys_paa(appdata.omraader(), seneste).set_index("omraade")
status = appdata.status_pr_omraade(raa, panel).join(po[["navn", "trafiklys", "lys_fra"]])
profil = appdata.saesonprofil(panel)

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
lys_fra = po["lys_fra"].max()
# Lusegrænsen er 0,5 – men 0,2 i forårsugerne, hvor vildlaksen vandrer ud. Den gældende grænse står i data.
graense = pd.to_numeric(talt.get("Lusegrense uke", pd.Series(dtype=str)).astype(str).str.replace(",", "."),
                        errors="coerce").mode()
graense = float(graense.iloc[0]) if len(graense) else 0.5
uge_nu = profil[profil["uge"] == iso.week].dropna(subset=["i_aar"])
over_snit = int((uge_nu["i_aar"] > uge_nu["snit"]).sum())
top_uge_pr_omr = profil.loc[profil.groupby("omraade")["snit"].idxmax()].set_index("omraade")["uge"]
syd_top, nord_top = int(top_uge_pr_omr.loc[[1, 2]].mean()), int(top_uge_pr_omr.loc[[12, 13]].mean())

retning = "lower" if aendring < 0 else "higher"

# Indberetningen halter: en uges tal indberettes i løbet af ugen efter. Vis hvilke uger der stadig mangler.
i_dag = pd.Timestamp.now(tz="Europe/Oslo").tz_localize(None).normalize()
mangler = [u.isocalendar().week for u in pd.date_range(seneste + pd.Timedelta(weeks=1),
                                                         i_dag - pd.Timedelta(days=i_dag.weekday() + 7), freq="W-MON")]
if not mangler:
    indberetning = "latest complete week"
elif len(mangler) == 1:
    indberetning = f"week {mangler[0]} is still being reported"
else:
    indberetning = f"weeks {mangler[0]}–{mangler[-1]} are still being reported"
# --- 2. Sidehoved og resumé ------------------------------------------------------------
st.markdown(sidehoved(
    f"Weekly brief · Sea lice in Norwegian salmon farming · Week {iso.week}, {iso.year} · latest complete week",
    f"Lice levels are {abs(aendring):.0%} {retning} than a year ago – pressure is highest in {status.loc[top, 'navn']}",
    "Weekly status on sea lice (lakselus) in all 13 production areas (produksjonsområder), based on the lice counts "
    "fish farms report to the Norwegian Food Safety Authority. Figures are set against the lice limit (lusegrense), "
    "the government traffic-light system (trafikklyssystemet) and the seasonal pattern of recent years.",
    [("live", appdata.opdatering_tekst(panel) + ("" if not mangler else f" · {indberetning}")), ("database", "BarentsWatch / Mattilsynet"),
     ("location_on", f"{len(talt)} sites in this week's figures"), ("verified", "Independent analysis of open data")],
), unsafe_allow_html=True)

st.markdown(resume([
    (tal(gns), f"adult female lice per fish on average along the coast in week {iso.week} – {abs(aendring):.0%} "
               f"{retning} than the same week last year ({tal(gns_sidst)})."),
    (f"{len(over)} of {len(talt)}", f"sites ({pct(len(over) / len(talt))}) were above the {tal(graense, 1)} lice limit"
                                    + ("; most in " + " and ".join(f"PO {o}" for o in over_pr_omr.index[:2]) if len(over) else "") + "."),
    (f"{len(roede)} of 13", f"production areas {'has' if len(roede) == 1 else 'have'} a red traffic light"
                            + (": " + ", ".join(roede["navn"]) if len(roede) else "")
                            + f". The colour is set by the government (latest decision {lys_fra:%b %Y}) from estimated lice "
                            "mortality in wild salmon – not from this week's counts. Red means a cut in production capacity."),
]), unsafe_allow_html=True)

# --- 3. Figur 1: kort og rangering -------------------------------------------------

# 3a. Valg og tilstand
# Kortet og søjlerne er forbundet: klik på et område (på kortet eller som søjle) viser hvert anlæg i området.
# Et nyt nøgletal (kort_n) tegner kort og graf forfra, så kortet zoomer ind på valget og markeringen nulstilles.
st.session_state.setdefault("po_valgt", None)
st.session_state.setdefault("lok_valgt", None)
st.session_state.setdefault("kort_n", 0)
n = st.session_state.kort_n


def vaelg(omraade: int | None, lokalitet: int | None = None) -> None:
    st.session_state.po_valgt, st.session_state.lok_valgt = omraade, lokalitet
    st.session_state.kort_n += 1


def fra_kort() -> None:
    objekter = [o for liste in st.session_state[f"kort_{n}"].selection.get("objects", {}).values() for o in liste]
    if objekter:
        o = objekter[0]
        vaelg(int(o["omraade"]), int(o["lokalitet"]) if "lokalitet" in o else None)


def fra_soejler() -> None:
    valg = st.session_state[f"rang_{n}"].selection.get("vaelg", [])
    if valg and "lokalitet" in valg[0]:
        vaelg(st.session_state.po_valgt, int(valg[0]["lokalitet"]))
    elif valg:
        vaelg(int(valg[0]["omraade"]))


def udsnit(polygon: list, bredde: int = 420, hoejde: int = 440) -> pdk.ViewState:
    """Kortudsnit, der rammer polygonet (web-mercator), så det valgte område fylder kortet."""
    lon, lat = [p[0] for p in polygon], [p[1] for p in polygon]
    y = lambda b: math.log(math.tan(math.pi / 4 + math.radians(b) / 2))
    midt_y = (y(max(lat)) + y(min(lat))) / 2
    zoom = min(math.log2(bredde / 512 * 360 / (max(lon) - min(lon))),  # deck.gl: verden er 512 px bred ved zoom 0
               math.log2(hoejde / 512 * 2 * math.pi / (y(max(lat)) - y(min(lat))))) - 0.2
    return pdk.ViewState(longitude=(max(lon) + min(lon)) / 2, latitude=math.degrees(2 * math.atan(math.exp(midt_y)) - math.pi / 2),
                         zoom=min(zoom, 8))


# 3b. Overskrift – konklusionen og den gældende lusegrænse står i titlen
valgt = st.session_state.po_valgt if st.session_state.po_valgt in status.index else None
over_tekst = "above" if status.loc[top, "hunlus"] > graense else "below"
st.markdown(figur(
    1, f"{status.loc[top, 'navn']} has the highest lice level among the larger areas ({tal(status.loc[top, 'hunlus'])}) – "
       f"{over_tekst} the {tal(graense, 1)} lice limit",
    f"Adult female lice per fish, week {iso.week} {iso.year}. Dots: sites, coloured by lice level. Area colour: the "
    "government traffic light, which reflects estimated harm to wild salmon – not this week's counts.",
), unsafe_allow_html=True)

venstre, hoejre = st.columns([1, 1.15], gap="large")
# 3c. Kort: områder farvet efter trafiklys, anlæg farvet efter lusetal
with venstre:
    st.markdown(f'<div class="korthjaelp">{ikon("touch_app")} Click an area on the map or a bar to see every site in it</div>',
                unsafe_allow_html=True)
    lok = talt.dropna(subset=["lat", "lon", "hunlus"]).assign(omraade=lambda d: d["omraade"].astype(int))
    i_valgt = (lok["omraade"] == valgt) if valgt else pd.Series(True, index=lok.index)
    lok["farve"] = [rgba(LUS_FARVER[lus_niveau(v)], 235 if v_ else 70) for v, v_ in zip(lok["hunlus"], i_valgt)]
    lok["tip"] = ("<b>" + lok["lokalitet_navn"] + "</b><br>PO " + lok["omraade"].astype(str) + " · "
                  + lok["hunlus"].map(tal) + " adult female lice per fish")
    lok = lok[["lon", "lat", "omraade", "lokalitet", "farve", "tip"]]
    po_kort = po.reset_index().join(status[["hunlus", "n_lok"]], on="omraade").assign(
        fyld=lambda d: [rgba(LYS_FARVER[c][0], 55 if o == valgt else 12 if valgt else 30) for c, o in zip(d["trafiklys"], d["omraade"])],
        kant=lambda d: [rgba(LYS_FARVER[c][0], 255 if o == valgt else 90 if valgt else 170) for c, o in zip(d["trafiklys"], d["omraade"])],
        tip=lambda d: "<b>PO " + d["omraade"].astype(str) + " · " + d["navn"] + "</b><br>"
                      + d["hunlus"].map(tal) + " adult female lice per fish · " + d["n_lok"].fillna(0).astype(int).astype(str)
                      + " sites<br>Traffic light: " + d["trafiklys"].map(appdata.TRAFIKLYS)
                      + " (decided " + d["lys_fra"].dt.strftime("%b %Y") + ")<br><i>Click to see its sites</i>",
    )[["omraade", "polygon", "fyld", "kant", "tip"]]
    lag = [
        pdk.Layer("PolygonLayer", po_kort, id="omraader", get_polygon="polygon", get_fill_color="fyld",
                  get_line_color="kant", line_width_min_pixels=1, pickable=True, auto_highlight=True,
                  highlight_color=[232, 96, 60, 70]),
        pdk.Layer("ScatterplotLayer", lok, id="anlaeg", get_position=["lon", "lat"], get_fill_color="farve",
                  get_radius=2400, radius_min_pixels=2.2 if not valgt else 4, radius_max_pixels=9, stroked=True,
                  get_line_color=[255, 255, 255], line_width_min_pixels=0.4, pickable=True, auto_highlight=True),
    ]
    if st.session_state.lok_valgt in set(lok["lokalitet"]):
        lag.append(pdk.Layer("ScatterplotLayer", lok[lok["lokalitet"] == st.session_state.lok_valgt], id="markeret",
                             get_position=["lon", "lat"], get_fill_color="farve", get_radius=2400, radius_min_pixels=8,
                             stroked=True, get_line_color=[11, 34, 48], line_width_min_pixels=2.5))
    st.pydeck_chart(pdk.Deck(
        layers=lag,
        initial_view_state=udsnit(po.loc[valgt, "polygon"]) if valgt else pdk.ViewState(latitude=65.0, longitude=14.2, zoom=3.25),
        views=[pdk.View(type="MapView", controller={"scrollZoom": False, "dragPan": True, "doubleClickZoom": True})],
        map_style=pdk.map_styles.CARTO_LIGHT,
        tooltip={"html": "{tip}", "style": {"backgroundColor": "#0B2230", "color": "#FFFFFF",
                                             "fontFamily": "Inter, sans-serif", "fontSize": "12px"}},
    ), height=440, on_select=fra_kort, selection_mode="single-object", key=f"kort_{n}")

# 3d. Søjler: alle områder – eller hvert anlæg i det valgte område
# Grænselinjer: 0,2 i forårsugerne og den almindelige grænse på 0,5. Teksterne står på hver sin linje.
graenser = pd.DataFrame({"x": [0.2, 0.5], "t": ["0.2 spring weeks", "0.5 lice limit"]})
linjer = alt.Chart(graenser).mark_rule(strokeDash=[3, 3], color="#D64545", opacity=.7).encode(x="x:Q")
linjetekst = (
    alt.Chart(graenser.iloc[[0]]).mark_text(align="left", dx=3, fontSize=10, color="#D64545")
    .encode(x="x:Q", y=alt.value(-16), text="t:N")
    + alt.Chart(graenser.iloc[[1]]).mark_text(align="right", dx=-3, fontSize=10, color="#D64545")
    .encode(x="x:Q", y=alt.value(-4), text="t:N")
)
farveskala = alt.Scale(domain=["lav", "mellem", "hoej"], range=[LUS_FARVER["lav"], LUS_FARVER["mellem"], LUS_FARVER["hoej"]])

with hoejre:
    if valgt is None:
        rang = status.reset_index().assign(
            etiket=lambda d: "PO " + d["omraade"].astype(str) + "  " + d["navn"] + d["n_lok"].map(lambda n_: " *" if n_ < MIN_LOK else ""),
            niveau=lambda d: d["hunlus"].map(lus_niveau),
            tekst=lambda d: d["hunlus"].map(tal),
            lille=lambda d: d["n_lok"] < MIN_LOK,
        )
        # Små områder nederst og nedtonet, så rangeringen stemmer med konklusionen (som kun bygger på de solide).
        rang = rang.sort_values(["lille", "hunlus"], ascending=[True, False])
        y = alt.Y("etiket:N", sort=list(rang["etiket"]), title=None, axis=alt.Axis(labelLimit=220, labelFontSize=11.5, labelColor="#1B2B36"))
        soejler = alt.Chart(rang).mark_bar(height=15, cursor="pointer").encode(
            x=alt.X("hunlus:Q", title="Adult female lice per fish", scale=alt.Scale(domain=[0, 0.55]),
                    axis=alt.Axis(format=".1f", tickCount=6, grid=True)),
            y=y,
            color=alt.Color("niveau:N", legend=None, scale=farveskala),
            opacity=alt.condition("datum.lille", alt.value(0.35), alt.value(1.0)),
            tooltip=[alt.Tooltip("etiket:N", title="Area"), alt.Tooltip("hunlus:Q", title="Female lice", format=".3f"),
                     alt.Tooltip("n_lok:Q", title="Sites")],
        ).add_params(alt.selection_point(name="vaelg", fields=["omraade"]))
        tekster = alt.Chart(rang).mark_text(align="left", dx=4, fontSize=11, color="#1B2B36").encode(
            x="hunlus:Q", y=y, text="tekst:N")
        st.altair_chart((soejler + tekster + linjer + linjetekst).properties(height=440), width="stretch",
                        on_select=fra_soejler, key=f"rang_{n}")
    else:
        s = status.loc[valgt]
        omr_tal = talt.loc[talt["omraade"] == valgt, "hunlus"].dropna()
        top_x = max(0.55, min(float(omr_tal.max()) * 1.12, 1.2))
        anlaeg = talt[talt["omraade"] == valgt].dropna(subset=["hunlus"]).sort_values("hunlus", ascending=False).assign(
            niveau=lambda d: d["hunlus"].map(lus_niveau), tekst=lambda d: d["hunlus"].map(tal),
            markeret=lambda d: d["lokalitet"] == st.session_state.lok_valgt,
            # Enkelte anlæg kan ligge langt over resten; aksen kappes, og søjlen ender i en pil med det rigtige tal.
            x_vis=lambda d: d["hunlus"].clip(upper=top_x), kappet=lambda d: d["hunlus"] > top_x,
            tekst_vis=lambda d: d["tekst"].where(~d["kappet"], d["tekst"] + " →"),
            # Navne kan gå igen – lokalitetsnummeret skiller dem ad på aksen.
            etiket=lambda d: d["lokalitet_navn"].where(~d["lokalitet_navn"].duplicated(keep=False),
                                                       d["lokalitet_navn"] + " (" + d["lokalitet"].astype(int).astype(str) + ")"),
        )
        n_over = int((anlaeg["over_graense"] == "Ja").sum())
        lys_kant, lys_bg, lys_tekst = LYS_FARVER[s.trafiklys]
        st.button("← All areas", on_click=vaelg, args=(None,), key="alle_omraader", type="tertiary")
        st.markdown(
            f'<div class="omraadehoved"><b>PO {valgt} · {s.navn}</b>'
            f'<span>{len(anlaeg)} sites · mean {tal(s.hunlus)} · {n_over} above the limit · '
            f'<i class="prik" style="background:{lys_kant}"></i>{appdata.TRAFIKLYS[s.trafiklys]} traffic light</span></div>',
            unsafe_allow_html=True)
        y = alt.Y("etiket:N", sort=list(anlaeg["etiket"]), title=None,
                  axis=alt.Axis(labelLimit=180, labelFontSize=11, labelColor="#1B2B36", labelOverlap=False))
        soejler = alt.Chart(anlaeg).mark_bar(height=11, cursor="pointer", stroke=FARVER["blaek"]).encode(
            x=alt.X("x_vis:Q", title="Adult female lice per fish", scale=alt.Scale(domain=[0, top_x]),
                    axis=alt.Axis(format=".1f", grid=True, orient="top")),
            y=y,
            color=alt.Color("niveau:N", legend=None, scale=farveskala),
            strokeWidth=alt.condition("datum.markeret", alt.value(2), alt.value(0)),
            tooltip=[alt.Tooltip("lokalitet_navn:N", title="Site"), alt.Tooltip("hunlus:Q", title="Female lice", format=".2f"),
                     alt.Tooltip("temp:Q", title="Sea temp. °C", format=".1f")],
        ).add_params(alt.selection_point(name="vaelg", fields=["lokalitet"]))
        tekster = alt.Chart(anlaeg).mark_text(align="left", dx=4, fontSize=10, color="#1B2B36").encode(
            x="x_vis:Q", y=y, text="tekst_vis:N")
        snit_linje = alt.Chart(pd.DataFrame({"x": [s.hunlus]})).mark_rule(color=FARVER["blaek"], strokeWidth=1.2).encode(x="x:Q")
        omr_graenser = alt.Chart(graenser).mark_rule(strokeDash=[4, 3], color="#D64545", strokeWidth=1.2).encode(x="x:Q")
        graf = soejler + tekster + snit_linje + omr_graenser
        # Lange områder rulles i en ramme med samme højde som kortet.
        with st.container(height=360, border=False):
            st.altair_chart(graf.properties(height=max(120, 17 * len(anlaeg))), width="stretch",
                            on_select=fra_soejler, key=f"rang_{n}")
        st.markdown(f'<div class="kilde">Bars: each site that counted lice in week {iso.week}. Solid line: area mean. '
                    f'Dashed: 0.2 and 0.5 limits. Click a bar to mark the site on the map.</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="forklaring">'
    f'<span><i class="prik" style="background:{LUS_FARVER["lav"]}"></i>Below 0.2</span>'
    f'<span><i class="prik" style="background:{LUS_FARVER["mellem"]}"></i>0.2–0.5</span>'
    f'<span><i class="prik" style="background:{LUS_FARVER["hoej"]}"></i>Above 0.5</span>'
    f'<span><i class="prik" style="background:{LYS_FARVER["green"][0]}"></i><i class="prik" style="background:{LYS_FARVER["yellow"][0]}"></i>'
    f'<i class="prik" style="background:{LYS_FARVER["red"][0]}"></i>Traffic light (area colour: government decision on wild-salmon risk)</span></div>',
    unsafe_allow_html=True,
)
st.markdown(kilde(f"Area figures are unweighted means over sites that counted lice that week. "
                  f"* Fewer than {MIN_LOK} sites (faded, at the bottom) – the figure is uncertain and excluded from the conclusions."),
            unsafe_allow_html=True)

# --- 4. Figur 2: statustabel ----------------------------------------------------------
st.markdown(figur(
    2, "Status by production area",
    "Lice level, change vs. the previous 4 weeks, share of sites above the limit and sea temperature.",
), unsafe_allow_html=True)

raekker = []
for o, s in status.iterrows():
    t_ikon, t_farve, t_tekst = trend(s.hunlus, s.hunlus_4u_foer)
    if pd.isna(s.hunlus_4u_foer) or not s.hunlus_4u_foer:
        aend_tekst = "–"
    elif max(s.hunlus, s.hunlus_4u_foer) < LAVT_NIVEAU:
        aend_tekst = f"{s.hunlus - s.hunlus_4u_foer:+.2f}".replace("-", "−")
    else:
        aend_tekst = pct(s.hunlus / s.hunlus_4u_foer - 1, True)
    farve = LUS_FARVER[lus_niveau(s.hunlus)]
    lys_kant, _, lys_tekst = LYS_FARVER[s.trafiklys]
    raekker.append(
        f'<tr><td class="po ekstra">{o}</td><td class="navn">{s.navn}{" <span style=\'color:#6B7A86\'>*</span>" if s.n_lok < MIN_LOK else ""}</td>'
        f'<td><i class="prik" style="background:{lys_kant}"></i><span class="ekstra">{appdata.TRAFIKLYS[s.trafiklys]}</span></td>'
        f'<td class="tal">{tal(s.hunlus)}<span class="minibar" style="width:{min(s.hunlus / 0.5, 1) * 60:.0f}px;background:{farve}"></span></td>'
        f'<td class="tal" style="color:{t_farve}"><span class="ekstra">{ikon(t_ikon, t_farve, t_tekst)}</span> {aend_tekst}</td>'
        f'<td class="tal" style="color:{"#D64545" if s.andel_over >= .1 else "inherit"}">{pct(s.andel_over)}</td>'
        f'<td class="tal ekstra">{tal(s.temp, 1)} °C</td><td class="tal ekstra">{int(s.n_lok)}</td></tr>'
    )
st.markdown(
    '<table class="tabel"><thead><tr><th class="ekstra">PO</th><th>Production area</th><th>Traffic<span class="ekstra"> light</span></th>'
    '<th class="tal">Female lice / fish</th><th class="tal">Δ 4 weeks</th><th class="tal">Above limit</th>'
    '<th class="tal ekstra">Sea temp.</th><th class="tal ekstra">Sites</th></tr></thead><tbody>'
    + "".join(raekker) + "</tbody></table>",
    unsafe_allow_html=True,
)
st.markdown(kilde(f"Δ 4 weeks: change vs. the mean of the four preceding weeks; below {LAVT_NIVEAU} lice per fish "
                  f"shown in lice per fish instead of percent. * Fewer than {MIN_LOK} sites."), unsafe_allow_html=True)

# --- 5. Figur 3: små multipler --------------------------------------------------------
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
nu_tal = basis.mark_text(align="left", dx=5, fontSize=10, fontWeight=600, color=FARVER["laks_tekst"]).encode(
    y="i_aar:Q", text=alt.Text("i_aar:Q", format=".2f")).transform_filter("datum.er_sidste")
def smaa_multipler(kolonner: int, bredde: int, hoejde: int) -> alt.FacetChart:
    return alt.layer(baand, snit, nu, nu_pkt, nu_tal, data=sm).properties(width=bredde, height=hoejde).facet(
        facet=alt.Facet("titel:N", sort=orden, header=alt.Header(labelFontSize=11, labelPadding=4)), columns=kolonner,
    ).resolve_scale(y="shared")


# Tre kolonner på brede skærme, én på mobil – CSS i udseende.py viser den ene og skjuler den anden.
with st.container(key="smaa_bred"):
    st.altair_chart(smaa_multipler(3, 225, 90), width="content")
with st.container(key="smaa_mobil"):
    st.altair_chart(smaa_multipler(1, 285, 64), width="content")
st.markdown(kilde(f"Week 53 is omitted. Mean and band are based on {foerste}–{i_aar - 1}."), unsafe_allow_html=True)

# --- 6. Figur 4: sæsonmønster ---------------------------------------------------------
st.markdown(figur(
    4, (f"The peak comes later the further north: around week {syd_top} in the south vs. week {nord_top} in Finnmark"
        if nord_top > syd_top else
        f"The lice peak comes around week {syd_top} in the south and week {nord_top} in Finnmark"),
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

# --- 7. Metode og forbehold -----------------------------------------------------------
st.markdown(
    '<div class="metode"><b>Method and caveats.</b> Data are weekly lice counts per site from BarentsWatch '
    "(reported to the Norwegian Food Safety Authority). Area figures are unweighted means over sites that counted "
    "lice that week; the number of fish per site is not included. Farms report a week's counts during the following "
    "week, so the brief usually trails the calendar by 1–2 weeks: the latest week is only included once at least "
    "80% of sites have reported. The lice limit is 0.5 adult female lice per fish (0.2 during the spring weeks). "
    "The traffic light is the colour the government had set for each production area in the week shown. It is decided "
    "every second year from estimated lice-induced mortality in wild salmon, so an area can be red even when its farms "
    "are below the lice limit. The analysis is independent "
    "and not prepared for or by any company.</div>",
    unsafe_allow_html=True,
)
